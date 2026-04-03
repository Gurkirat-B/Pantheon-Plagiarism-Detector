import JSZip from "jszip";

const SOURCE_EXTENSIONS = [".java", ".cpp", ".c", ".h"];

export async function zipHasValidSource(
  zip: JSZip,
  depth = 0,
): Promise<boolean> {
  if (depth > 10) return false;
  for (const [name, entry] of Object.entries(zip.files)) {
    if (entry.dir) continue;
    if (SOURCE_EXTENSIONS.some((ext) => name.endsWith(ext))) return true;
    if (name.endsWith(".zip")) {
      try {
        const buf = await entry.async("arraybuffer");
        const nested = await JSZip.loadAsync(buf);
        if (await zipHasValidSource(nested, depth + 1)) return true;
      } catch {
        // skip unreadable nested zip
      }
    }
  }
  return false;
}
