interface SearchBoxProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

export function SearchBox({ value, onChange, placeholder = 'Search...' }: SearchBoxProps) {
  return (
    <input
      className="search-box"
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
    />
  );
}
