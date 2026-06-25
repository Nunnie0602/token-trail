import type { Direction, Point } from "../types/game";
import { GRID_COLS, GRID_ROWS } from "./constants";

const OPPOSITE: Record<Direction, Direction> = {
  UP: "DOWN",
  DOWN: "UP",
  LEFT: "RIGHT",
  RIGHT: "LEFT",
};

export function resolveDirection(
  current: Direction,
  next: Direction,
): Direction {
  if (OPPOSITE[current] === next) {
    return current;
  }
  return next;
}

export function isWallCollision(point: Point): boolean {
  return (
    point.x < 0 ||
    point.y < 0 ||
    point.x >= GRID_COLS ||
    point.y >= GRID_ROWS
  );
}

export function isSelfCollision(head: Point, body: Point[]): boolean {
  return body.some((segment) => segment.x === head.x && segment.y === head.y);
}

export function getNextHead(head: Point, direction: Direction): Point {
  switch (direction) {
    case "UP":
      return { x: head.x, y: head.y - 1 };
    case "DOWN":
      return { x: head.x, y: head.y + 1 };
    case "LEFT":
      return { x: head.x - 1, y: head.y };
    case "RIGHT":
      return { x: head.x + 1, y: head.y };
  }
}
