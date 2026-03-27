import { useRef, useState } from 'react';

interface FileUploadProps {
  label: string;
  accept: string;
  multiple?: boolean;
  onFiles: (files: File[]) => void;
  status?: string;
}

export function FileUpload({ label, accept, multiple, onFiles, status }: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    onFiles(Array.from(files));
  }

  function onDragOver(e: React.DragEvent) {
    e.preventDefault();
    setDragging(true);
  }

  function onDragLeave() {
    setDragging(false);
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    handleFiles(e.dataTransfer.files);
  }

  function onClick() {
    inputRef.current?.click();
  }

  return (
    <div className="mb-3">
      <span className="label">{label}</span>
      <div
        className={`border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors ${
          dragging
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-gray-400 bg-gray-50'
        }`}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={onClick}
      >
        <svg
          className="mx-auto mb-2 text-gray-400"
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>
        <p className="text-xs text-gray-500">
          {multiple ? 'Drop CSV files here or click to browse' : 'Drop a CSV file here or click to browse'}
        </p>
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          className="hidden"
          onChange={e => handleFiles(e.target.files)}
        />
      </div>
      {status && (
        <p className="mt-1 text-xs text-gray-600">{status}</p>
      )}
    </div>
  );
}
