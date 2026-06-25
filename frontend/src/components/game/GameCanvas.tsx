import { useEffect, useRef } from "react";
import { SnakeEngine } from "../../engine/snakeEngine";
import { spawnFoodsOnGrid } from "../../engine/gridSpawner";
import { GRID_COLS, GRID_ROWS } from "../../engine/constants";
import type { Direction, PlacedFood } from "../../types/game";

type GameCanvasProps = {
  headText: string;
  foods: PlacedFood[];
  onEatFood: (food: PlacedFood) => void;
  onCollision: (type: "wall" | "self") => void;
  onFpsUpdate: (fps: number) => void;
  onEngineReady?: (engine: SnakeEngine) => void;
  paused?: boolean;
};

const KEY_MAP: Record<string, Direction> = {
  ArrowUp: "UP",
  ArrowDown: "DOWN",
  ArrowLeft: "LEFT",
  ArrowRight: "RIGHT",
  w: "UP",
  W: "UP",
  s: "DOWN",
  S: "DOWN",
  a: "LEFT",
  A: "LEFT",
  d: "RIGHT",
  D: "RIGHT",
};

export function GameCanvas({
  headText,
  foods,
  onEatFood,
  onCollision,
  onFpsUpdate,
  onEngineReady,
  paused = false,
}: GameCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const engineRef = useRef<SnakeEngine | null>(null);
  const initialHeadRef = useRef(headText);
  const callbacksRef = useRef({ onEatFood, onCollision, onFpsUpdate, onEngineReady });

  callbacksRef.current = { onEatFood, onCollision, onFpsUpdate, onEngineReady };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const startX = Math.floor(GRID_COLS / 2);
    const startY = Math.floor(GRID_ROWS / 2);
    const engine = new SnakeEngine(canvas, {
      onEatFood: (food) => callbacksRef.current.onEatFood(food),
      onCollision: (type) => callbacksRef.current.onCollision(type),
      onFpsUpdate: (fps) => callbacksRef.current.onFpsUpdate(fps),
    });

    engine.initSnake({
      x: startX,
      y: startY,
      text: initialHeadRef.current,
    });
    engine.setFoods(foods);
    engine.start();
    engineRef.current = engine;
    callbacksRef.current.onEngineReady?.(engine);

    const handleKeyDown = (event: KeyboardEvent) => {
      const direction = KEY_MAP[event.key];
      if (direction) {
        event.preventDefault();
        engine.setDirection(direction);
      }
    };

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      engine.stop();
      engineRef.current = null;
    };
  }, []);

  useEffect(() => {
    const engine = engineRef.current;
    if (!engine) {
      return;
    }
    engine.setFoods(foods);
  }, [foods]);

  useEffect(() => {
    const engine = engineRef.current;
    if (!engine) {
      return;
    }
    engine.paused = paused;
  }, [paused]);

  return (
    <div className="game-canvas-wrap">
      <canvas ref={canvasRef} className="game-canvas" />
    </div>
  );
}

export function createPlacedFoods(
  tokens: Parameters<typeof spawnFoodsOnGrid>[0],
  occupied: { x: number; y: number }[],
): PlacedFood[] {
  return spawnFoodsOnGrid(tokens, GRID_COLS, GRID_ROWS, occupied);
}
