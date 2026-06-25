import type { Direction, PlacedFood, Point } from "../types/game";
import {
  BASE_MOVE_INTERVAL_MS,
  CELL_SIZE,
  GRID_COLS,
  GRID_ROWS,
  MAX_SNAKE_LENGTH,
} from "./constants";
import {
  getNextHead,
  isSelfCollision,
  isWallCollision,
  resolveDirection,
} from "./collision";

export type SnakeSegment = Point & { text: string };

export type SnakeEngineCallbacks = {
  onEatFood?: (food: PlacedFood) => void;
  onCollision?: (type: "wall" | "self") => void;
  onFpsUpdate?: (fps: number) => void;
};

export class SnakeEngine {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private animationId: number | null = null;
  private lastMoveTime = 0;
  private moveInterval = BASE_MOVE_INTERVAL_MS;
  private direction: Direction = "RIGHT";
  private nextDirection: Direction = "RIGHT";
  private frameCount = 0;
  private lastFpsTime = 0;
  private callbacks: SnakeEngineCallbacks;

  snake: SnakeSegment[] = [];
  foods: PlacedFood[] = [];
  running = false;
  paused = false;

  constructor(canvas: HTMLCanvasElement, callbacks: SnakeEngineCallbacks = {}) {
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      throw new Error("Canvas 2D context unavailable");
    }
    this.canvas = canvas;
    this.ctx = ctx;
    this.callbacks = callbacks;
    this.resize();
  }

  resize(): void {
    this.canvas.width = GRID_COLS * CELL_SIZE;
    this.canvas.height = GRID_ROWS * CELL_SIZE;
  }

  setFoods(foods: PlacedFood[]): void {
    this.foods = foods;
  }

  setMoveInterval(interval: number): void {
    this.moveInterval = interval;
  }

  initSnake(head: SnakeSegment, body: SnakeSegment[] = []): void {
    this.snake = [...body, head];
    this.direction = "RIGHT";
    this.nextDirection = "RIGHT";
  }

  setDirection(direction: Direction): void {
    this.nextDirection = resolveDirection(this.direction, direction);
  }

  start(): void {
    if (this.running) {
      return;
    }
    this.running = true;
    this.lastMoveTime = performance.now();
    this.lastFpsTime = this.lastMoveTime;
    this.frameCount = 0;
    this.loop(this.lastMoveTime);
  }

  stop(): void {
    this.running = false;
    if (this.animationId !== null) {
      cancelAnimationFrame(this.animationId);
      this.animationId = null;
    }
  }

  private loop(timestamp: number): void {
    if (!this.running) {
      return;
    }

    this.animationId = requestAnimationFrame((next) => this.loop(next));

    if (!this.paused && timestamp - this.lastMoveTime >= this.moveInterval) {
      this.step();
      this.lastMoveTime = timestamp;
    }

    this.render();
    this.trackFps(timestamp);
  }

  trimToMaxLength(maxLength: number): void {
    while (this.snake.length > maxLength) {
      this.snake.shift();
    }
  }

  getOccupiedCells(): Point[] {
    return this.snake.map((segment) => ({ x: segment.x, y: segment.y }));
  }

  private step(): void {
    if (this.snake.length === 0) {
      return;
    }

    this.direction = this.nextDirection;
    const head = this.snake[this.snake.length - 1];
    const nextHead = getNextHead(head, this.direction);

    if (isWallCollision(nextHead)) {
      this.callbacks.onCollision?.("wall");
      this.stop();
      return;
    }

    const body = this.snake.slice(0, -1);
    if (isSelfCollision(nextHead, body)) {
      this.callbacks.onCollision?.("self");
      this.stop();
      return;
    }

    const foodIndex = this.foods.findIndex(
      (food) => food.x === nextHead.x && food.y === nextHead.y,
    );

    if (foodIndex >= 0) {
      const eaten = this.foods[foodIndex];
      this.foods = this.foods.filter((_, index) => index !== foodIndex);
      this.snake.push({ ...nextHead, text: eaten.text });
      this.trimToMaxLength(MAX_SNAKE_LENGTH);
      this.callbacks.onEatFood?.(eaten);
      return;
    }

    const newHead: SnakeSegment = { ...nextHead, text: head.text };
    this.snake.push(newHead);
    this.snake.shift();
  }

  private trackFps(timestamp: number): void {
    this.frameCount += 1;
    const elapsed = timestamp - this.lastFpsTime;
    if (elapsed >= 1000) {
      const fps = Math.round((this.frameCount * 1000) / elapsed);
      this.callbacks.onFpsUpdate?.(fps);
      this.frameCount = 0;
      this.lastFpsTime = timestamp;
    }
  }

  private render(): void {
    const { ctx } = this;
    ctx.fillStyle = "#f7f7f5";
    ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    ctx.strokeStyle = "#e5e5e0";
    ctx.lineWidth = 1;
    for (let x = 0; x <= GRID_COLS; x += 1) {
      ctx.beginPath();
      ctx.moveTo(x * CELL_SIZE, 0);
      ctx.lineTo(x * CELL_SIZE, GRID_ROWS * CELL_SIZE);
      ctx.stroke();
    }
    for (let y = 0; y <= GRID_ROWS; y += 1) {
      ctx.beginPath();
      ctx.moveTo(0, y * CELL_SIZE);
      ctx.lineTo(GRID_COLS * CELL_SIZE, y * CELL_SIZE);
      ctx.stroke();
    }

    for (const food of this.foods) {
      this.drawFood(food);
    }

    this.snake.forEach((segment, index) => {
      const isHead = index === this.snake.length - 1;
      this.drawSegment(segment, isHead);
    });
  }

  private drawSegment(segment: SnakeSegment, isHead: boolean): void {
    const padding = 2;
    const x = segment.x * CELL_SIZE + padding;
    const y = segment.y * CELL_SIZE + padding;
    const size = CELL_SIZE - padding * 2;

    this.ctx.fillStyle = isHead ? "#1a1a1a" : "#3d3d3d";
    this.ctx.fillRect(x, y, size, size);

    if (isHead) {
      this.ctx.strokeStyle = "#ffffff";
      this.ctx.lineWidth = 2;
      this.ctx.strokeRect(x, y, size, size);
    }

    this.ctx.fillStyle = isHead ? "#ffffff" : "#e8e8e4";
    this.ctx.font = "10px 'Segoe UI', sans-serif";
    this.ctx.textAlign = "center";
    this.ctx.textBaseline = "middle";
    const label =
      segment.text.length > 5 ? `${segment.text.slice(0, 4)}…` : segment.text;
    this.ctx.fillText(label, x + size / 2, y + size / 2);
  }

  private drawFood(food: PlacedFood): void {
    const padding = 3;
    const x = food.x * CELL_SIZE + padding;
    const y = food.y * CELL_SIZE + padding;
    const size = CELL_SIZE - padding * 2;

    this.ctx.strokeStyle = "#1a1a1a";
    this.ctx.lineWidth = 1;
    this.ctx.strokeRect(x, y, size, size);

    this.ctx.fillStyle = "#1a1a1a";
    this.ctx.font = "9px 'Segoe UI', sans-serif";
    this.ctx.textAlign = "center";
    this.ctx.textBaseline = "top";
    const label =
      food.text.length > 4 ? `${food.text.slice(0, 3)}…` : food.text;
    this.ctx.fillText(label, x + size / 2, y + 4);
    this.ctx.fillStyle = "#6b6b6b";
    this.ctx.font = "8px 'Segoe UI', sans-serif";
    this.ctx.fillText(`(${food.prob.toFixed(2)})`, x + size / 2, y + size - 10);
  }
}
