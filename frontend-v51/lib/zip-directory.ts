import { zip } from "fflate";

/** Plafond backend `src/assembler/zip_validator.py` (MAX_ZIP_SIZE_MB=100). */
export const MAX_SERVER_ZIP_BYTES = 100 * 1024 * 1024;
/** Le pic RAM inclut buffers source + buffer ZIP + overhead JS (≈2x ou plus). */
const BROWSER_ZIP_RAM_SAFETY_FACTOR = 2;
const MAX_BROWSER_ZIP_RAM_BYTES = 400 * 1024 * 1024;
/** Taille totale des fichiers source tolérée avant compression locale. */
export const MAX_FOLDER_SOURCE_BYTES = Math.floor(
  MAX_BROWSER_ZIP_RAM_BYTES / BROWSER_ZIP_RAM_SAFETY_FACTOR,
);

function sanitizeZipBasename(name: string): string {
  const s = name.replace(/[^\w\-.]+/g, "_").replace(/^_|_$/g, "");
  return s.slice(0, 80) || "fournisseurs";
}

/**
 * Construit un fichier .zip à partir d’une sélection « dossier » (webkitdirectory).
 * Les chemins relatifs dans le ZIP reprennent `webkitRelativePath` (sous-dossiers inclus).
 */
export async function fileListToSupplierZipFile(
  fileList: FileList,
): Promise<File> {
  if (!fileList?.length) {
    throw new Error("Dossier vide : aucun fichier à compresser.");
  }

  let totalSize = 0;
  const files: File[] = [];
  for (let i = 0; i < fileList.length; i++) {
    const file = fileList[i]!;
    const rel = (file as File & { webkitRelativePath?: string })
      .webkitRelativePath;
    if (!rel) {
      throw new Error(
        "Sélection invalide : utilisez « Choisir un dossier » (pas un fichier seul).",
      );
    }
    if (rel.endsWith("/")) {
      continue;
    }
    totalSize += file.size;
    files.push(file);
  }

  if (files.length === 0) {
    throw new Error("Aucun fichier exploitable dans ce dossier.");
  }

  if (totalSize > MAX_FOLDER_SOURCE_BYTES) {
    throw new Error(
      `Le dossier dépasse environ ${Math.round(MAX_FOLDER_SOURCE_BYTES / (1024 * 1024))} Mo de fichiers source pour une compression locale sûre. Compressez en ZIP sur votre poste et utilisez l’envoi fichier.`,
    );
  }

  const entries: Record<string, Uint8Array> = {};
  for (const file of files) {
    const rel = (file as File & { webkitRelativePath?: string })
      .webkitRelativePath!;
    const buf = new Uint8Array(await file.arrayBuffer());
    entries[rel] = buf;
  }

  const firstRel = (files[0] as File & { webkitRelativePath?: string })
    .webkitRelativePath!;
  const rootName = firstRel.includes("/")
    ? firstRel.slice(0, firstRel.indexOf("/"))
    : firstRel;

  const zipped: Uint8Array = await new Promise((resolve, reject) => {
    zip(entries, { level: 6 }, (err, out) => {
      if (err) {
        reject(err);
        return;
      }
      resolve(out);
    });
  });

  if (zipped.byteLength > MAX_SERVER_ZIP_BYTES) {
    throw new Error(
      `ZIP final trop volumineux (${Math.round(zipped.byteLength / (1024 * 1024))} Mo). Limite serveur : ${Math.round(MAX_SERVER_ZIP_BYTES / (1024 * 1024))} Mo.`,
    );
  }

  const blob = new Blob([zipped as unknown as BlobPart], {
    type: "application/zip",
  });
  return new File([blob], `${sanitizeZipBasename(rootName)}.zip`, {
    type: "application/zip",
  });
}
