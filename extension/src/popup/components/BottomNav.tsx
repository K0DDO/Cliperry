import type { ScreenId } from "../lib/labels";

const ITEMS: Array<{ id: ScreenId; label: string; icon: string }> = [
  { id: "main", label: "Main", icon: "◆" },
  { id: "history", label: "History", icon: "☰" },
  { id: "settings", label: "Settings", icon: "◎" },
];

interface Props {
  active: ScreenId;
  onChange: (screen: ScreenId) => void;
}

export function BottomNav({ active, onChange }: Props) {
  return (
    <nav className="nav glass" aria-label="Cliperry navigation">
      {ITEMS.map((item) => (
        <button
          key={item.id}
          type="button"
          className={`nav__item ${active === item.id ? "nav__item--active" : ""}`}
          onClick={() => onChange(item.id)}
        >
          <span className="nav__icon" aria-hidden="true">
            {item.icon}
          </span>
          <span className="nav__label">{item.label}</span>
        </button>
      ))}
    </nav>
  );
}
