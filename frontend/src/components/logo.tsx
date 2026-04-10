type LogoProps = {
  size?: number;
  className?: string;
};

export function Logo({ size = 36, className }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="Applyflow logo"
      role="img"
    >
      <rect width="40" height="40" rx="11" fill="#1c1917" />
      <path d="M8 13.5 L21.5 13.5" stroke="white" strokeWidth="2" strokeLinecap="round" opacity="0.3" />
      <path d="M8 20 L18 20" stroke="white" strokeWidth="2" strokeLinecap="round" opacity="0.55" />
      <path d="M8 26.5 L13.5 26.5" stroke="white" strokeWidth="2" strokeLinecap="round" opacity="0.9" />
      <path d="M27 31 L27 13.5" stroke="#2dd4bf" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M22 19 L27 13.5 L32 19" stroke="#2dd4bf" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
