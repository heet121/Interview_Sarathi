"""
Local answer enrichment — no LLM API required.

Uses pattern matching, curated snippets, and question-type logic to produce
specific reference answers instead of generic templates.
"""

from __future__ import annotations

import math
import re
from typing import Optional

# ── Curated answers for common interview questions (exact / substring match) ──

_SNIPPETS: list[tuple[str, str]] = [
    ("sort an array of 0s, 1s and 2s", "Use the Dutch National Flag algorithm (3-pointer): low, mid, high. Swap 0s to front, 2s to end, scan with mid pointer. Time O(n), space O(1). One pass, in-place."),
    ("count inversions", "Use merge sort: while merging, count pairs where left element > right element. Time O(n log n), space O(n). Each inversion counted during merge step."),
    ("mirror tree", "Recursively swap left and right children at every node (DFS or BFS). Base case: null node. Time O(n), space O(h) for recursion stack."),
    ("middle of a given linked list", "Two pointers: slow moves 1 step, fast moves 2 steps. When fast reaches end, slow is at middle. Time O(n), space O(1)."),
    ("two numbers that add up to a target", "Hash map: for each value x, check if (target - x) exists. Store seen numbers. Time O(n), space O(n)."),
    ("longest substring without repeating", "Sliding window + set/map of last index. Expand right, shrink left on duplicate. Time O(n), space O(min(n, alphabet))."),
    ("lru cache", "Hash map + doubly linked list: map key→node, move accessed nodes to head, evict tail when capacity exceeded. get/put O(1)."),
    ("median from a data stream", "Two heaps: max-heap for lower half, min-heap for upper half. Balance sizes so median is top of max-heap or average of both tops. Insert O(log n)."),
    ("merge k sorted linked lists", "Min-heap of size k: push head of each list, pop smallest, push its next. Time O(N log k), space O(k)."),
    ("lowest common ancestor", "Recursive DFS on BST: if both nodes smaller go left, both larger go right, else current node is LCA. For binary tree: post-order return node if it matches p or q or both subtrees non-null."),
    ("valid bst", "In-order traversal should be strictly increasing, or pass min/max bounds recursively."),
    ("number of islands", "DFS/BFS on grid: mark visited '1' cells, count connected components. Time O(rows×cols)."),
    ("merge overlapping intervals", "Sort by start, iterate merging if current overlaps previous (start <= prev.end). Time O(n log n)."),
    ("edit distance", "DP: dp[i][j] = min edits to convert s1[:i] to s2[:j]. Fill using insert/delete/replace. Time O(mn), space O(mn) or O(min(m,n)) optimized."),
    ("word break", "DP: dp[i] = true if s[:i] can be segmented using dictionary words ending at i."),
    ("design a url shortener", "Requirements: encode/decode, high read QPS. Use base62 hash of auto-increment ID or MD5 prefix. Store in DB + Redis cache. Discuss collision handling, TTL, analytics, rate limits."),
    ("design uber", "Matching: geohash/grid partition drivers/riders. Real-time location in Redis, dispatch nearest available. Surge = f(supply/demand). Payments with idempotency keys. Handle split-brain with regional failover."),
    ("design netflix", "CDN edge caching, adaptive bitrate streaming (HLS/DASH), encoding pipeline (transcode ladder), recommendation (collaborative + content), chaos monkey for resilience."),
    ("design news feed", "Fan-out on write for celebrities, fan-out on read for normal users. Rank by affinity, recency, engagement. Cache hot feeds in Redis. Use Kafka for event pipeline."),
    ("acid properties", "Atomicity: all-or-nothing transaction. Consistency: valid state before/after. Isolation: concurrent txs don't interfere (levels: RC, RR, serializable). Durability: committed data survives crash (WAL)."),
    ("normalization", "1NF: atomic columns. 2NF: no partial dependency on composite key. 3NF: no transitive dependency. Reduces redundancy; may denormalize for read performance."),
    ("process vs thread", "Process: own memory space, heavier context switch. Thread: shared address space within process, lighter switch, needs sync (mutex). Use threads for parallel I/O-bound; processes for isolation."),
    ("virtual memory", "Maps virtual addresses to physical via page tables. Pages swapped to disk on pressure. TLB caches translations. Page fault loads page from disk."),
    ("deadlock", "Four conditions: mutual exclusion, hold-and-wait, no preemption, circular wait. Prevent by ordering locks, timeouts, or banker's algorithm."),
    ("tcp vs udp", "TCP: connection-oriented, reliable, ordered, congestion control — HTTP, files. UDP: connectionless, faster, may lose packets — video, DNS, gaming."),
    ("https", "TLS handshake: client hello → server cert → key exchange → symmetric encryption. Certificate signed by CA. Protects integrity and confidentiality on wire."),
    ("tell me about yourself", "Structure: present (role/skills) → past (1-2 relevant projects) → future (why this role/company). 90 seconds, end with why you're a strong fit."),
    ("2 to the power of 24", "2^24 = 16,777,216. Quick check: 2^10≈1K, 2^20≈1M, 2^24 = 2^20 × 2^4 ≈ 1,048,576 × 16 = 16,777,216."),
    ("merge sort and quick sort", "Merge sort: avg/worst O(n log n), stable, O(n) extra space. Quick sort: avg O(n log n), worst O(n²) without good pivot, in-place, usually faster in practice."),
    ("heap sort over merge sort", "Heap sort: O(1) extra space (in-place), O(n log n) worst case. Merge sort needs O(n) auxiliary space. Prefer heap when memory is tight."),
    ("consistent hashing", "Hash nodes and keys to ring; key goes to next clockwise node. Adding/removing node only remaps K/n keys. Used in distributed caches and load balancers."),
    ("cap theorem", "In partition, choose Consistency (all nodes see same data, may block) or Availability (always respond, may be stale). Partition tolerance required in distributed systems."),
    ("microservices vs monolith", "Monolith: simpler deploy, shared DB, good for small teams. Microservices: independent scale/deploy, network overhead, need observability and API contracts."),
]

_NUMERIC_PATTERNS = [
    (re.compile(r"2\s*(\^|\*\*|to the power of)\s*24", re.I), "2^24 = 16,777,216."),
    (re.compile(r"2\s*(\^|\*\*|to the power of)\s*10", re.I), "2^10 = 1,024."),
    (re.compile(r"2\s*(\^|\*\*|to the power of)\s*16", re.I), "2^16 = 65,536."),
]


def _match_snippet(question: str) -> Optional[str]:
    q = question.lower()
    for key, ans in _SNIPPETS:
        if key in q:
            return ans
    return None


def _try_numeric(question: str) -> Optional[str]:
    for pat, ans in _NUMERIC_PATTERNS:
        if pat.search(question):
            return f"Answer: {ans} Show brief calculation steps if asked to derive."
    return None


def _coding_answer(question: str, company: str) -> str:
    q = question.lower()
    parts = []

    if "linked list" in q:
        parts.append("Clarify singly vs doubly linked, constraints on memory.")
        if "reverse" in q or "k nodes" in q:
            parts.append("Use iterative reversal in groups of k; handle remainder < k. Time O(n), space O(1).")
        elif "cycle" in q:
            parts.append("Floyd's tortoise-hare: slow+fast pointers; if they meet, cycle exists.")
        elif "middle" in q:
            parts.append("Two-pointer (slow/fast) technique.")
        else:
            parts.append("Draw examples; watch edge cases: empty list, single node.")
    elif "binary tree" in q or "bst" in q or "tree" in q:
        parts.append("State traversal order (in/pre/post) or recursion invariant.")
        if "lca" in q or "ancestor" in q:
            parts.append("Recursive DFS with base cases; BST uses ordering property.")
        else:
            parts.append("Typical solutions: DFS/BFS O(n) time, O(h) space.")
    elif "array" in q:
        if "product" in q and "except" in q:
            parts.append("Prefix and suffix products in two passes without division. Time O(n), space O(n) or O(1) with output array.")
        elif "maximum" in q and "range" in q:
            parts.append("Segment tree or sparse table for range max queries; or sqrt decomposition.")
        elif "inversion" in q:
            parts.append("Merge sort counting during merge — O(n log n).")
        else:
            parts.append("Consider sorting, two pointers, prefix sums, or hash map depending on constraint.")
    elif "string" in q or "dictionary" in q or "word" in q:
        parts.append("Trie, DP, or backtracking common. Clarify dictionary size and repetition rules.")
    elif "design" in q:
        parts.append("Requirements → API → data model → scaling → failure modes. Estimate QPS/storage.")
    else:
        parts.append("Restate problem, examples, brute force then optimize.")

    parts.append(f"State time/space complexity and test edge cases for {company}.")
    return " ".join(parts)


def enrich_answer_local(question: str, company: str, round_type: str) -> str:
    """Return a question-specific reference answer without any LLM."""
    snip = _match_snippet(question)
    if snip:
        return snip

    num = _try_numeric(question)
    if num:
        return num

    rt = (round_type or "general").lower()
    q = question.lower()

    if rt in ("coding", "dsa") or any(k in q for k in ("implement", "given an", "given a", "array", "linked list", "tree")):
        return _coding_answer(question, company or "the company")

    if rt == "system_design" or "design a" in q or "design the" in q:
        return (
            f"Clarify scale (users, QPS, data size). List core APIs. "
            f"Draw services, DB, cache, queue. Discuss sharding, replication, bottlenecks. "
            f"Mention monitoring and how {company} scale systems handle peak load."
        )

    if rt == "hr" or any(k in q for k in ("tell me about", "describe a time", "why do you", "weakness", "conflict")):
        return (
            f"Use STAR format tailored to: \"{question[:80]}…\". "
            f"Situation in one sentence, your specific actions (not the team), measurable result. "
            f"Connect the lesson to {company}'s values and the role."
        )

    if rt == "dbms" or any(k in q for k in ("sql", "database", "index", "transaction", "acid")):
        return (
            "Define the term precisely, explain why it matters in production, "
            "give a concrete example (e.g. banking transaction), mention trade-offs or common mistakes."
        )

    if rt == "operating_system" or any(k in q for k in ("process", "thread", "memory", "kernel", "scheduling")):
        return (
            "Explain the mechanism, relate to real OS behavior (Linux/Windows), "
            "cover trade-offs and one debugging or performance implication."
        )

    if rt == "telephonic":
        return "Give the direct answer first, then one line of reasoning. State assumptions before calculating."

    if rt == "networking":
        return "Explain step-by-step flow, name protocols and ports, mention failure modes and latency impact."

    return (
        f"Direct answer first, then 2–3 supporting points with a concrete example. "
        f"Keep it interview-length (90–120s spoken) and relevant to {company}."
    )
