// CodeEditor.jsx
// --------------
// Wraps @monaco-editor/react (the same editor engine that powers VS Code)
// to provide syntax highlighting, line numbers, and a familiar editing
// experience for the code being reviewed.

import Editor from "@monaco-editor/react";

/**
 * @param {Object} props
 * @param {string} props.code - Current code content.
 * @param {(value: string) => void} props.onChange - Called on every keystroke with the updated code.
 * @param {string} props.language - Monaco language mode (e.g. "python", "javascript").
 */
export default function CodeEditor({ code, onChange, language }) {
  return (
    <div className="code-editor-wrapper">
      <Editor
        height="480px"
        language={language}
        value={code}
        theme="vs-dark"
        onChange={(value) => onChange(value ?? "")}
        options={{
          minimap: { enabled: false },
          fontSize: 14,
          scrollBeyondLastLine: false,
          automaticLayout: true,
          wordWrap: "on",
          tabSize: 4,
        }}
      />
    </div>
  );
}
