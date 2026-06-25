const NAME_PREFIXES = ["不願具名", "低調", "隱姓埋名"] as const;

const QING_OFFICIAL_TITLES = [
  "四庫全書編纂官",
  "翰林院編修",
  "內閣學士",
  "順天府尹",
  "禮部侍郎",
  "刑部主事",
  "兵部員外郎",
  "都察院御史",
] as const;

export const PLAYER_NAME_MAX_LENGTH = 15;

export function generateDefaultPlayerName(): string {
  const prefix =
    NAME_PREFIXES[Math.floor(Math.random() * NAME_PREFIXES.length)];
  const title =
    QING_OFFICIAL_TITLES[
      Math.floor(Math.random() * QING_OFFICIAL_TITLES.length)
    ];
  return sanitizePlayerName(`${prefix}的${title}`);
}

export function sanitizePlayerName(raw: string): string {
  const stripped = raw
    .replace(/[<>"'&]/g, "")
    .replace(/[\u0000-\u001f\u007f]/g, "")
    .trim();

  return stripped.slice(0, PLAYER_NAME_MAX_LENGTH);
}
