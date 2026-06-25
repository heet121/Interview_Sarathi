"""
Curated + generated interview questions by round_type.
Used to expand beyond grg124 (~440) to 2500+ company-tagged entries.
"""

from __future__ import annotations

import itertools
from typing import Dict, List, Tuple

# ── Static pools (real interview-style prompts) ─────────────────

CODING = [
    "Given an array of integers, find two numbers that add up to a target sum.",
    "Reverse a linked list in groups of size k.",
    "Find the longest substring without repeating characters.",
    "Merge k sorted linked lists into one sorted list.",
    "Given a binary tree, find the lowest common ancestor of two nodes.",
    "Implement LRU cache with O(1) get and put.",
    "Find the median from a data stream.",
    "Given a matrix of 0s and 1s, find the largest square submatrix of all 1s.",
    "Serialize and deserialize a binary tree.",
    "Find all anagrams of a pattern in a string.",
    "Given a rotated sorted array, search for a target value.",
    "Implement a trie with insert, search, and prefix search.",
    "Find the shortest path in a grid with obstacles elimination.",
    "Given an array, find the maximum product subarray.",
    "Detect cycle in a directed graph.",
    "Find the kth largest element in an unsorted array.",
    "Given intervals, merge overlapping intervals.",
    "Implement pow(x, n) with O(log n) time.",
    "Find the number of islands in a 2D grid.",
    "Given a string, find the longest palindromic substring.",
    "Implement a min-stack supporting push, pop, top, and getMin in O(1).",
    "Find the edit distance between two strings.",
    "Given a binary search tree, validate whether it is a valid BST.",
    "Find the word break problem solution for a given dictionary.",
    "Implement next permutation for an array of numbers.",
    "Given a list of tasks with cooldown, find minimum intervals needed.",
    "Find maximum sum path in a binary tree.",
    "Implement regular expression matching with '.' and '*'.",
    "Given a string of digits, return all possible letter combinations.",
    "Find minimum window substring containing all characters of a pattern.",
]

DSA = [
    "Explain the time and space complexity of Quick Sort and when it degrades.",
    "What is the difference between a stack and a queue? Give real-world examples.",
    "How does a hash map work internally? Explain collision resolution strategies.",
    "Compare array list vs linked list for insert, delete, and random access.",
    "What is a balanced binary search tree? Why are AVL and Red-Black trees used?",
    "Explain BFS vs DFS with use cases in interview problems.",
    "What is dynamic programming? Explain overlapping subproblems and optimal substructure.",
    "How does Dijkstra's algorithm work and when does it fail?",
    "Explain topological sorting and where it is used.",
    "What is the difference between recursion and iteration for tree traversals?",
    "How would you detect a cycle in a linked list?",
    "Explain heap data structure and its use in priority queues.",
    "What is trie and when would you prefer it over a hash map?",
    "Compare merge sort, quick sort, and heap sort for stability and memory.",
    "Explain union-find (disjoint set) and path compression.",
    "What is a segment tree and what problems does it solve?",
    "Explain sliding window technique with an example.",
    "What is two-pointer technique? Give two problem patterns.",
    "How does binary search work on answer (search space reduction)?",
    "Explain graph representations: adjacency list vs adjacency matrix.",
]

DBMS = [
    "Explain ACID properties with a banking transaction example.",
    "What is normalization? Explain 1NF, 2NF, and 3NF.",
    "Difference between clustered and non-clustered index.",
    "What is a transaction isolation level? Explain READ COMMITTED vs SERIALIZABLE.",
    "Explain CAP theorem in the context of distributed databases.",
    "What is sharding and how is it different from replication?",
    "Explain optimistic vs pessimistic locking.",
    "What is a covering index and when does it help?",
    "Explain write-ahead logging (WAL) in databases.",
    "What is N+1 query problem and how do you fix it?",
    "Compare SQL vs NoSQL — when would you pick each?",
    "Explain database connection pooling and why it matters.",
    "What is a deadlock in DBMS and how can it be prevented?",
    "Explain B+ tree index structure used in databases.",
    "What is eventual consistency and where is it acceptable?",
]

OS = [
    "Explain process vs thread with memory and scheduling differences.",
    "What is virtual memory and how does paging work?",
    "Explain deadlock conditions and prevention strategies.",
    "What is context switching and why is it expensive?",
    "Difference between mutex and semaphore.",
    "Explain CPU scheduling algorithms: FCFS, SJF, Round Robin.",
    "What is thrashing in operating systems?",
    "Explain user mode vs kernel mode.",
    "What is copy-on-write in fork()?",
    "Explain the producer-consumer problem and solutions.",
    "What is a system call? Give examples.",
    "Explain paging vs segmentation.",
    "What is an orphan process vs zombie process?",
    "How does an OS handle page faults?",
    "Explain inter-process communication (IPC) mechanisms.",
]

SYSTEM_DESIGN = [
    "Design a URL shortener like bit.ly.",
    "Design a rate limiter for an API gateway.",
    "Design a notification system (email, SMS, push).",
    "Design a chat application like WhatsApp.",
    "Design a news feed system like Facebook.",
    "Design a ride-hailing matching system like Uber.",
    "Design a video streaming platform like Netflix.",
    "Design a distributed cache like Redis.",
    "Design a search autocomplete system.",
    "Design a payment processing system with idempotency.",
    "Design a ticket booking system for flash sales.",
    "Design a file storage system like Google Drive.",
    "Design a metrics and monitoring system.",
    "Design a job scheduler for millions of tasks.",
    "Design a leaderboard system with real-time updates.",
]

HR = [
    "Tell me about yourself.",
    "Why do you want to join our company?",
    "Describe a time you handled conflict in a team.",
    "Tell me about a project you are most proud of.",
    "Describe a situation where you failed and what you learned.",
    "How do you handle tight deadlines with unclear requirements?",
    "Tell me about a time you had to learn something quickly.",
    "Describe a time you disagreed with your manager.",
    "What is your biggest weakness and how are you improving it?",
    "Where do you see yourself in five years?",
    "Why should we hire you over other candidates?",
    "Describe a time you showed leadership without formal authority.",
    "How do you prioritize when everything is urgent?",
    "Tell me about a time you improved a process at work or college.",
    "Describe your most challenging bug and how you fixed it.",
]

TECHNICAL = [
    "Explain how HTTPS works end to end.",
    "What happens when you type a URL in the browser?",
    "Explain REST vs GraphQL trade-offs.",
    "What is the difference between TCP and UDP?",
    "Explain OAuth 2.0 authorization code flow.",
    "What is CDN and why does it improve latency?",
    "Explain microservices vs monolith architecture.",
    "What is idempotency in APIs and why does it matter?",
    "Explain load balancing strategies.",
    "What is caching and which cache invalidation strategies exist?",
    "Explain message queues and when to use Kafka vs RabbitMQ.",
    "What is circuit breaker pattern in distributed systems?",
    "Explain horizontal vs vertical scaling.",
    "What is API versioning and backward compatibility?",
    "Explain CI/CD pipeline stages for a web application.",
]

TELEPHONIC = [
    "What is the approximate value of 2^24?",
    "What is the time complexity of merge sort in average and worst case?",
    "What does find() return when an element is not in a C++ map?",
    "Name common implementations of the Map interface in Java.",
    "What is the advantage of heap sort over merge sort in memory usage?",
    "Convert a binary number to decimal without using built-in functions.",
    "What is the difference between pass by value and pass by reference?",
    "Explain Big-O notation in one minute.",
    "What is a singleton design pattern?",
    "What is the difference between abstract class and interface?",
]

NETWORKING = [
    "Explain the OSI model layers briefly.",
    "What is DNS and how does resolution work?",
    "Explain three-way TCP handshake.",
    "What is HTTP/2 improvement over HTTP/1.1?",
    "What is a reverse proxy vs forward proxy?",
    "Explain WebSocket vs HTTP long polling.",
    "What is CORS and why does it exist?",
    "Explain SSL/TLS handshake at high level.",
    "What is NAT and why is it used?",
    "Explain subnetting with a simple example.",
]

# Company-specific flavor suffixes for generated variants
COMPANY_FOCUS = {
    "Google": ["search", "scale", "maps", "distributed systems"],
    "Amazon": ["e-commerce", "AWS", "leadership principles", "customer obsession"],
    "Microsoft": ["cloud", "Azure", "productivity", "enterprise"],
    "Facebook": ["social graph", "feed ranking", "real-time", "ads"],
    "Netflix": ["streaming", "CDN", "recommendations", "chaos engineering"],
    "Uber": ["marketplace", "GPS", "surge pricing", "real-time matching"],
    "Flipkart": ["flash sales", "inventory", "logistics", "payments"],
    "PayPal": ["payments", "fraud detection", "financial compliance", "transactions"],
    "Adobe": ["creative tools", "graphics", "plugins", "collaboration"],
    "Samsung": ["mobile", "embedded", "hardware-software", "performance"],
}

ROUND_POOLS: Dict[str, List[str]] = {
    "coding": CODING,
    "dsa": DSA,
    "dbms": DBMS,
    "operating_system": OS,
    "system_design": SYSTEM_DESIGN,
    "hr": HR,
    "technical": TECHNICAL,
    "telephonic": TELEPHONIC,
    "networking": NETWORKING,
    "general": HR + TECHNICAL,
    "miscellaneous": TECHNICAL + DSA,
    "aptitude": TELEPHONIC,
    "managerial": HR,
}


def _variants(base: str, company: str, n: int = 3) -> List[str]:
    """Light paraphrases so the same concept can fill gaps per company."""
    focus = COMPANY_FOCUS.get(company, ["software engineering"])
    out = [base]
    for f in focus[: max(0, n - 1)]:
        out.append(f"{base} (Context: {company} — {f})")
    return out


def expansion_for_company(company: str, needed: int, seen: set) -> List[Tuple[str, str]]:
    """
    Return up to `needed` (round_type, question) pairs not in `seen`.
    seen keys are (company, normalized_question).
    """
    added: List[Tuple[str, str]] = []
    round_order = [
        "coding", "dsa", "system_design", "technical", "dbms",
        "operating_system", "hr", "telephonic", "networking", "general",
    ]
    for rt in round_order:
        pool = ROUND_POOLS.get(rt, [])
        for q in pool:
            for variant in _variants(q, company, 2):
                key = (company, " ".join(variant.split()).lower())
                if key in seen:
                    continue
                seen.add(key)
                added.append((rt, variant))
                if len(added) >= needed:
                    return added
    return added
