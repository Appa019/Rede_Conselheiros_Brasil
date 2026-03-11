interface CvmLogoProps {
  className?: string;
}

export function CvmLogo({ className }: CvmLogoProps) {
  return (
    <svg
      viewBox="0 0 28 28"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <rect width="28" height="28" fill="#1B5E4B" />
      <text
        x="14"
        y="19"
        textAnchor="middle"
        fill="white"
        fontFamily="var(--font-heading), 'Space Grotesk', sans-serif"
        fontWeight="700"
        fontSize="13"
        letterSpacing="-0.5"
      >
        CVM
      </text>
    </svg>
  );
}
