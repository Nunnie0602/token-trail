export function buildStoryText(tokens: string[]): string {
  if (tokens.length === 0) {
    return "";
  }
  if (tokens.length === 1) {
    return `${tokens[0]}......。`;
  }

  const [head, ...rest] = tokens;
  const tail = rest.pop()!;
  const middle = rest.join("");

  return `${head}，${middle}${tail}......。`;
}
