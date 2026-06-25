/** Heuristics to avoid Windows Phone Link / mobile-as-webcam virtual devices. */
const REMOTE_CAMERA =
  /phone\s*link|link\s*to\s*windows|your\s*phone|mobile\s*device|android|iphone|ipad|continuity|droidcam|iriun|epoccam|camo|wireless\s*camera|remote\s*camera|galaxy/i

const LAPTOP_CAMERA =
  /integrated|built-?in|internal|facetime|webcam|hd\s*camera|truevision|thinkpad|lenovo|dell|acer|asus|hp\s|surface|logitech/i

export function isRemoteCameraLabel(label: string): boolean {
  return REMOTE_CAMERA.test(label)
}

export function pickWebcamDevice(devices: MediaDeviceInfo[]): MediaDeviceInfo | null {
  const video = devices.filter((d) => d.kind === 'videoinput')
  if (!video.length) return null

  const labeled = video.filter((d) => d.label)
  const pool = labeled.length ? labeled : video

  const laptop = pool.find((d) => LAPTOP_CAMERA.test(d.label) && !isRemoteCameraLabel(d.label))
  if (laptop) return laptop

  const local = pool.find((d) => !isRemoteCameraLabel(d.label))
  if (local) return local

  return pool[0] ?? null
}

export async function listVideoInputs(): Promise<MediaDeviceInfo[]> {
  if (!navigator.mediaDevices?.enumerateDevices) return []
  const devices = await navigator.mediaDevices.enumerateDevices()
  return devices.filter((d) => d.kind === 'videoinput')
}

/** Labels are blank until camera permission is granted at least once. */
export async function listVideoInputsWithLabels(): Promise<MediaDeviceInfo[]> {
  let devices = await listVideoInputs()
  if (devices.length && !devices.some((d) => d.label)) {
    try {
      const tmp = await navigator.mediaDevices.getUserMedia({ video: true, audio: false })
      tmp.getTracks().forEach((t) => t.stop())
      devices = await listVideoInputs()
    } catch {
      /* permission denied — return unlabeled list */
    }
  }
  return devices
}

export function videoConstraintsForDevice(deviceId?: string): MediaTrackConstraints {
  const base: MediaTrackConstraints = {
    width: { ideal: 1280 },
    height: { ideal: 720 },
  }
  if (deviceId) base.deviceId = { ideal: deviceId }
  return base
}

export async function resolvePreferredDeviceId(preferredId?: string): Promise<string | undefined> {
  const devices = await listVideoInputsWithLabels()
  if (!devices.length) return preferredId

  if (preferredId && devices.some((d) => d.deviceId === preferredId)) {
    return preferredId
  }
  return pickWebcamDevice(devices)?.deviceId
}

export async function openWebcamStream(deviceId?: string): Promise<MediaStream> {
  const resolvedId = await resolvePreferredDeviceId(deviceId)
  return navigator.mediaDevices.getUserMedia({
    audio: false,
    video: videoConstraintsForDevice(resolvedId),
  })
}

export function cameraLabel(device: MediaDeviceInfo, index: number): string {
  const raw = device.label?.trim()
  if (raw) return raw
  return `Camera ${index + 1}`
}
