"use client";

import { create } from "zustand";

interface KanbanStore {
  selectedTaskId: string | null;
  isDrawerOpen: boolean;
  toasts: Toast[];
  setSelectedTaskId: (id: string | null) => void;
  openDrawer: (taskId: string) => void;
  closeDrawer: () => void;
  addToast: (toast: Omit<Toast, "id">) => void;
  removeToast: (id: string) => void;
}

export interface Toast {
  id: string;
  message: string;
  type: "success" | "error" | "info";
}

export const useKanbanStore = create<KanbanStore>((set) => ({
  selectedTaskId: null,
  isDrawerOpen: false,
  toasts: [],

  setSelectedTaskId: (id) => set({ selectedTaskId: id }),

  openDrawer: (taskId) =>
    set({ selectedTaskId: taskId, isDrawerOpen: true }),

  closeDrawer: () => set({ isDrawerOpen: false }),

  addToast: (toast) =>
    set((s) => ({
      toasts: [...s.toasts, { ...toast, id: crypto.randomUUID() }],
    })),

  removeToast: (id) =>
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));
