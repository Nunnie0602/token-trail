import type { PlacedFood, Point, TokenFood } from "../types/game";

function shuffle<T>(items: T[]): T[] {
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

export function isOccupied(point: Point, occupied: Point[]): boolean {
  return occupied.some((cell) => cell.x === point.x && cell.y === point.y);
}

export function getFreeCells(
  gridCols: number,
  gridRows: number,
  occupied: Point[],
): Point[] {
  const free: Point[] = [];
  for (let y = 0; y < gridRows; y += 1) {
    for (let x = 0; x < gridCols; x += 1) {
      const cell = { x, y };
      if (!isOccupied(cell, occupied)) {
        free.push(cell);
      }
    }
  }
  return free;
}

export function spawnFoodsOnGrid(
  tokens: TokenFood[],
  gridCols: number,
  gridRows: number,
  occupied: Point[],
): PlacedFood[] {
  const freeCells = shuffle(getFreeCells(gridCols, gridRows, occupied));
  const count = Math.min(tokens.length, freeCells.length);
  return tokens.slice(0, count).map((token, index) => ({
    ...token,
    ...freeCells[index],
  }));
}
