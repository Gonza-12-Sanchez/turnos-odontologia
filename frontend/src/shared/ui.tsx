export function Notice({ children }: { children: React.ReactNode }) {
  return <p className="notice" role="alert">{children}</p>
}
