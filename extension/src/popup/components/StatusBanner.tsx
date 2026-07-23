interface Props {
  tone?: "loading" | "error" | "success" | "info";
  children: string;
}

export function StatusBanner({ tone = "info", children }: Props) {
  return (
    <div className={`banner banner--${tone}`} role="status">
      <span className="banner__dot" aria-hidden="true" />
      <span>{children}</span>
    </div>
  );
}
