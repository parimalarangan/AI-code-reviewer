// LanguageSelector.jsx
// --------------------
// A small controlled <select> dropdown that lets the user tell Monaco (and
// the backend) which language the pasted code is written in. Kept as its
// own component so App.jsx doesn't get cluttered with the option list.

const SUPPORTED_LANGUAGES = [
  { value: "python", label: "Python" },
  { value: "javascript", label: "JavaScript" },
  { value: "typescript", label: "TypeScript" },
  { value: "java", label: "Java" },
  { value: "go", label: "Go" },
  { value: "csharp", label: "C#" },
  { value: "cpp", label: "C++" },
  { value: "rust", label: "Rust" },
];

/**
 * @param {Object} props
 * @param {string} props.value - Currently selected language value.
 * @param {(value: string) => void} props.onChange - Called with the new language when the user picks one.
 */
export default function LanguageSelector({ value, onChange }) {
  return (
    <select
      className="language-selector"
      value={value}
      onChange={(event) => onChange(event.target.value)}
      aria-label="Select programming language"
    >
      {SUPPORTED_LANGUAGES.map((lang) => (
        <option key={lang.value} value={lang.value}>
          {lang.label}
        </option>
      ))}
    </select>
  );
}
