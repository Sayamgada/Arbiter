import type { ScenarioIcon } from "@/lib/scenarios";

type Props = {
  icon: ScenarioIcon;
};

export default function ScenarioIcon({ icon }: Props) {
  const common = {
    width: 22,
    height: 22,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.7,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };

  switch (icon) {
    case "shield-check":
      return (
        <svg {...common}>
          <path d="M12 3l7 3v5c0 4.5-2.9 8.3-7 10-4.1-1.7-7-5.5-7-10V6l7-3z" />
          <path d="m8.5 12 2.2 2.2 4.8-4.8" />
        </svg>
      );

    case "shield-alert":
      return (
        <svg {...common}>
          <path d="M12 3l7 3v5c0 4.5-2.9 8.3-7 10-4.1-1.7-7-5.5-7-10V6l7-3z" />
          <path d="M12 8v4" />
          <path d="M12 15.5h.01" />
        </svg>
      );

    case "shield-x":
      return (
        <svg {...common}>
          <path d="M12 3l7 3v5c0 4.5-2.9 8.3-7 10-4.1-1.7-7-5.5-7-10V6l7-3z" />
          <path d="m9 9 6 6" />
          <path d="m15 9-6 6" />
        </svg>
      );

    case "wallet":
      return (
        <svg {...common}>
          <path d="M4 6.5A2.5 2.5 0 0 1 6.5 4H19a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H6.5A2.5 2.5 0 0 1 4 17.5v-11z" />
          <path d="M4 7h13" />
          <path d="M16 13h4" />
          <circle cx="16" cy="13" r=".7" />
        </svg>
      );

    case "package":
      return (
        <svg {...common}>
          <path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3z" />
          <path d="m4.5 7.5 7.5 4 7.5-4" />
          <path d="M12 11.5V21" />
        </svg>
      );

    case "scale":
      return (
        <svg {...common}>
          <path d="M12 4v16" />
          <path d="M6 6h12" />
          <path d="M6 6 3 12h6L6 6z" />
          <path d="m18 6-3 6h6l-3-6z" />
          <path d="M8 20h8" />
        </svg>
      );

    case "repeat":
      return (
        <svg {...common}>
          <path d="M17 2l4 4-4 4" />
          <path d="M3 11V9a3 3 0 0 1 3-3h15" />
          <path d="m7 22-4-4 4-4" />
          <path d="M21 13v2a3 3 0 0 1-3 3H3" />
        </svg>
      );

    case "lock-check":
      return (
        <svg {...common}>
          <rect
            x="5"
            y="10"
            width="14"
            height="11"
            rx="2"
          />
          <path d="M8 10V7a4 4 0 0 1 8 0v3" />
          <path d="m9 15 2 2 4-4" />
        </svg>
      );

    default:
      return null;
  }
}