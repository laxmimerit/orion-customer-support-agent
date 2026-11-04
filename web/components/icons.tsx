// Stroke icons from the design. All are decorative: the words beside them carry the meaning.
type IconProps = { size?: number; strokeWidth?: number };

function Icon({ size = 18, strokeWidth = 1.8, children }: IconProps & { children: React.ReactNode }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={strokeWidth}
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {children}
    </svg>
  );
}

export const TicketsIcon = (p: IconProps) => <Icon {...p}><path d="M4 13l2.5-7h11L20 13v6H4z" /><path d="M4 13h5l1 2h4l1-2h5" /></Icon>;
export const CustomersIcon = (p: IconProps) => <Icon {...p}><circle cx="9" cy="8" r="3.5" /><path d="M3 20c.8-3.5 3.2-5 6-5s5.2 1.5 6 5" /><path d="M16 4.5a3.5 3.5 0 0 1 0 7M18 15c1.6.6 2.6 2.2 3 5" /></Icon>;
export const KnowledgeIcon = (p: IconProps) => <Icon {...p}><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5z" /><path d="M4 20.5A2.5 2.5 0 0 1 6.5 18H20v3H6.5" /></Icon>;
export const ReportsIcon = (p: IconProps) => <Icon {...p}><path d="M4 20h16" /><path d="M7 16v-5M12 16V6M17 16v-8" /></Icon>;
export const CompanyIcon = (p: IconProps) => <Icon {...p}><path d="M4 21V5a1 1 0 0 1 1-1h9a1 1 0 0 1 1 1v16" /><path d="M15 9h4a1 1 0 0 1 1 1v11" /><path d="M3 21h18" /><path d="M8 8h3M8 12h3M8 16h3" /></Icon>;
export const SettingsIcon = (p: IconProps) => <Icon {...p}><path d="M4 6h9M17 6h3M4 12h3M11 12h9M4 18h11M19 18h1" /><circle cx="15" cy="6" r="2" /><circle cx="9" cy="12" r="2" /><circle cx="17" cy="18" r="2" /></Icon>;

export const SearchIcon = (p: IconProps) => <Icon size={16} strokeWidth={2} {...p}><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></Icon>;
export const LockIcon = (p: IconProps) => <Icon size={13} strokeWidth={2.2} {...p}><rect x="5" y="11" width="14" height="9" rx="2" /><path d="M8 11V8a4 4 0 0 1 8 0v3" /></Icon>;
export const ChevronIcon = (p: IconProps) => <Icon size={12} strokeWidth={2.4} {...p}><path d="M9 6l6 6-6 6" /></Icon>;
export const BackIcon = (p: IconProps) => <Icon size={15} strokeWidth={2.2} {...p}><path d="M19 12H5M11 18l-6-6 6-6" /></Icon>;
export const ForwardIcon = (p: IconProps) => <Icon size={16} strokeWidth={2.2} {...p}><path d="M5 12h14M13 6l6 6-6 6" /></Icon>;
export const CheckIcon = (p: IconProps) => <Icon size={16} strokeWidth={2.4} {...p}><path d="M5 12l5 5 9-10" /></Icon>;
export const FilterIcon = (p: IconProps) => <Icon size={15} strokeWidth={2} {...p}><path d="M4 5h16l-6 8v5l-4 2v-7z" /></Icon>;
export const AlertIcon = (p: IconProps) => <Icon size={20} strokeWidth={2} {...p}><circle cx="12" cy="12" r="9" /><path d="M12 7.5v5.5M12 16.5v.01" /></Icon>;
export const TableIcon = (p: IconProps) => <Icon size={15} strokeWidth={2} {...p}><rect x="3" y="5" width="18" height="14" rx="2" /><path d="M3 10h18M9 10v9" /></Icon>;

export const WebIcon = (p: IconProps) => <Icon size={15} strokeWidth={1.9} {...p}><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3c2.5 2.7 3.8 5.7 3.8 9s-1.3 6.3-3.8 9c-2.5-2.7-3.8-5.7-3.8-9S9.5 5.7 12 3z" /></Icon>;
export const ApiIcon = (p: IconProps) => <Icon size={15} strokeWidth={1.9} {...p}><path d="M8 7l-5 5 5 5M16 7l5 5-5 5" /></Icon>;
export const ChatIcon = (p: IconProps) => <Icon size={15} strokeWidth={1.9} {...p}><path d="M4 5h16v11H9l-5 4z" /></Icon>;
export const EmailIcon = (p: IconProps) => <Icon size={15} strokeWidth={1.9} {...p}><rect x="3" y="5" width="18" height="14" rx="2" /><path d="M3 7l9 6 9-6" /></Icon>;
