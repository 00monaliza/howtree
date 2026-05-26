"use client";

import { useLocale } from "next-intl";
import { usePathname, useRouter } from "@/lib/i18n/navigation";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const LOCALES = [
  { value: "ru", label: "RU", flag: "🇷🇺" },
  { value: "kk", label: "KK", flag: "🇰🇿" },
  { value: "en", label: "EN", flag: "🇬🇧" },
] as const;

export function LanguageSwitcher() {
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();

  function handleChange(newLocale: string) {
    router.replace(pathname, { locale: newLocale });
  }

  const current = LOCALES.find((l) => l.value === locale) ?? LOCALES[0];

  return (
    <Select value={locale} onValueChange={handleChange}>
      <SelectTrigger className="h-7 w-[76px] border-border bg-secondary text-xs font-medium gap-1">
        <SelectValue>
          <span className="flex items-center gap-1">
            {current.flag} {current.label}
          </span>
        </SelectValue>
      </SelectTrigger>
      <SelectContent className="bg-card border-border min-w-[76px]">
        {LOCALES.map(({ value, label, flag }) => (
          <SelectItem
            key={value}
            value={value}
            className="text-xs text-foreground focus:bg-secondary"
          >
            {flag} {label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
