import * as React from "react";
import {
  FileText,
  FileSpreadsheet,
  FileImage,
  FileCode2,
  FileArchive,
  FileVideo,
  FileAudio,
  File,
  Presentation,
  FileType,
} from "lucide-react";

import { cn } from "@/lib/utils";

export interface FileIconProps extends React.HTMLAttributes<HTMLDivElement> {
  extension: string;
  size?: number;
}

const extensionMap: Record<string, { icon: React.ElementType; className: string }> = {
  // PDF
  pdf: { icon: FileText, className: "file-pdf" },
  // Word
  doc: { icon: FileText, className: "file-doc" },
  docx: { icon: FileText, className: "file-doc" },
  // PowerPoint
  ppt: { icon: Presentation, className: "file-ppt" },
  pptx: { icon: Presentation, className: "file-ppt" },
  // Excel
  xls: { icon: FileSpreadsheet, className: "file-xls" },
  xlsx: { icon: FileSpreadsheet, className: "file-xls" },
  csv: { icon: FileSpreadsheet, className: "file-xls" },
  // Markdown
  md: { icon: FileText, className: "file-md" },
  markdown: { icon: FileText, className: "file-md" },
  // LaTeX
  tex: { icon: FileText, className: "file-tex" },
  latex: { icon: FileText, className: "file-tex" },
  // Code
  py: { icon: FileCode2, className: "file-code" },
  js: { icon: FileCode2, className: "file-code" },
  ts: { icon: FileCode2, className: "file-code" },
  tsx: { icon: FileCode2, className: "file-code" },
  jsx: { icon: FileCode2, className: "file-code" },
  html: { icon: FileCode2, className: "file-code" },
  css: { icon: FileCode2, className: "file-code" },
  json: { icon: FileCode2, className: "file-code" },
  // Images
  jpg: { icon: FileImage, className: "file-img" },
  jpeg: { icon: FileImage, className: "file-img" },
  png: { icon: FileImage, className: "file-img" },
  gif: { icon: FileImage, className: "file-img" },
  svg: { icon: FileImage, className: "file-img" },
  webp: { icon: FileImage, className: "file-img" },
  // Audio
  mp3: { icon: FileAudio, className: "file-audio" },
  wav: { icon: FileAudio, className: "file-audio" },
  ogg: { icon: FileAudio, className: "file-audio" },
  flac: { icon: FileAudio, className: "file-audio" },
  // Video
  mp4: { icon: FileVideo, className: "file-video" },
  avi: { icon: FileVideo, className: "file-video" },
  mov: { icon: FileVideo, className: "file-video" },
  mkv: { icon: FileVideo, className: "file-video" },
  webm: { icon: FileVideo, className: "file-video" },
  // Archives
  zip: { icon: FileArchive, className: "file-zip" },
  rar: { icon: FileArchive, className: "file-zip" },
  "7z": { icon: FileArchive, className: "file-zip" },
  tar: { icon: FileArchive, className: "file-zip" },
  gz: { icon: FileArchive, className: "file-zip" },
};

function FileIcon({ extension, size = 20, className, ...props }: FileIconProps) {
  const ext = extension.toLowerCase();
  const config = extensionMap[ext];
  const Icon = config?.icon ?? File;
  const colorClass = config?.className ?? "";

  return (
    <div className={cn("inline-flex", className)} {...props}>
      <Icon className={cn(colorClass)} style={{ width: size, height: size }} />
    </div>
  );
}

export { FileIcon };
