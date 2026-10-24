import { Component, type ReactNode } from "react";

interface WebGLBoundaryProps {
  children: ReactNode;
  fallback: ReactNode;
}

interface WebGLBoundaryState {
  hasError: boolean;
}

// Check if WebGL is available in this browser
function isWebGLAvailable(): boolean {
  try {
    const canvas = document.createElement("canvas");
    const context =
      canvas.getContext("webgl2") || canvas.getContext("webgl");
    return context !== null;
  } catch {
    return false;
  }
}

export class WebGLBoundary extends Component<
  WebGLBoundaryProps,
  WebGLBoundaryState
> {
  constructor(props: WebGLBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): WebGLBoundaryState {
    return { hasError: true };
  }

  override componentDidCatch(error: Error) {
    console.warn("WebGL render error:", error.message);
  }

  override render() {
    // If render error occurred or WebGL is not available, show fallback
    if (this.state.hasError || !isWebGLAvailable()) {
      return this.props.fallback;
    }

    return this.props.children;
  }
}
