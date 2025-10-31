#!/usr/bin/env python3
"""
Simple 1D Heat Equation Simulation

This is a sample physics simulation that solves the 1D heat equation
using finite differences. It's designed to be fast and deterministic
for testing and demonstration purposes.

The heat equation: ∂u/∂t = α ∂²u/∂x²
where u is temperature, t is time, x is position, and α is thermal diffusivity.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any

import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt


def solve_heat_equation(
    length: float = 1.0,
    time_steps: int = 1000,
    spatial_steps: int = 100,
    diffusivity: float = 0.01,
    initial_temp: float = 100.0,
    boundary_temp: float = 0.0,
    end_time: float = 1.0,
) -> Dict[str, Any]:
    """
    Solve 1D heat equation using explicit finite difference method
    
    Args:
        length: Length of the rod (m)
        time_steps: Number of time steps
        spatial_steps: Number of spatial grid points
        diffusivity: Thermal diffusivity (m²/s)
        initial_temp: Initial temperature in the center (°C)
        boundary_temp: Temperature at boundaries (°C)
        end_time: Total simulation time (s)
        
    Returns:
        Dictionary containing simulation results and metadata
    """
    
    # Grid setup
    dx = length / (spatial_steps - 1)
    dt = end_time / time_steps
    x = np.linspace(0, length, spatial_steps)
    
    # Stability criterion (Courant number)
    courant = diffusivity * dt / (dx ** 2)
    if courant > 0.5:
        print(f"WARNING: Courant number {courant:.3f} > 0.5, simulation may be unstable")
    
    # Initialize temperature array
    u = np.zeros((time_steps + 1, spatial_steps))
    
    # Initial condition: Gaussian temperature distribution
    center = length / 2
    width = length / 10
    u[0, :] = initial_temp * np.exp(-((x - center) / width) ** 2)
    
    # Boundary conditions (fixed temperature at ends)
    u[:, 0] = boundary_temp
    u[:, -1] = boundary_temp
    
    # Time stepping using explicit finite difference
    for n in range(time_steps):
        for i in range(1, spatial_steps - 1):
            u[n + 1, i] = u[n, i] + courant * (u[n, i + 1] - 2 * u[n, i] + u[n, i - 1])
    
    # Calculate some statistics
    max_temp = np.max(u)
    min_temp = np.min(u)
    final_max_temp = np.max(u[-1, :])
    center_temp_history = u[:, spatial_steps // 2]
    
    return {
        "temperature_field": u,
        "x_coordinates": x,
        "time_array": np.linspace(0, end_time, time_steps + 1),
        "parameters": {
            "length": length,
            "time_steps": time_steps,
            "spatial_steps": spatial_steps,
            "diffusivity": diffusivity,
            "initial_temp": initial_temp,
            "boundary_temp": boundary_temp,
            "end_time": end_time,
            "dx": dx,
            "dt": dt,
            "courant_number": courant,
        },
        "statistics": {
            "max_temperature": max_temp,
            "min_temperature": min_temp,
            "final_max_temperature": final_max_temp,
            "center_temperature_final": center_temp_history[-1],
        },
        "center_temperature_history": center_temp_history,
    }


def save_results(results: Dict[str, Any], output_dir: str = "/tmp/output") -> None:
    """Save simulation results to files"""
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Save metadata as JSON
    metadata = {
        "simulation_type": "1D_heat_equation",
        "timestamp": datetime.utcnow().isoformat(),
        "parameters": results["parameters"],
        "statistics": results["statistics"],
    }
    
    with open(os.path.join(output_dir, "meta.json"), "w") as f:
        json.dump(metadata, f, indent=2)
    
    # Save temperature data as CSV
    temp_data = results["temperature_field"]
    x_coords = results["x_coordinates"]
    time_array = results["time_array"]
    
    # Create CSV with time series of center temperature
    center_temp = results["center_temperature_history"]
    csv_data = np.column_stack((time_array, center_temp))
    
    np.savetxt(
        os.path.join(output_dir, "result.csv"),
        csv_data,
        delimiter=",",
        header="time_s,center_temperature_C",
        comments="",
    )
    
    # Save full temperature field as numpy array
    np.save(os.path.join(output_dir, "temperature_field.npy"), temp_data)
    np.save(os.path.join(output_dir, "x_coordinates.npy"), x_coords)
    np.save(os.path.join(output_dir, "time_array.npy"), time_array)
    
    # Create visualization
    create_plots(results, output_dir)
    
    print(f"Results saved to: {output_dir}")
    print(f"Files created: meta.json, result.csv, temperature_field.npy, plots")


def create_plots(results: Dict[str, Any], output_dir: str) -> None:
    """Create visualization plots"""
    
    temp_field = results["temperature_field"]
    x_coords = results["x_coordinates"]
    time_array = results["time_array"]
    center_temp = results["center_temperature_history"]
    
    # Create figure with subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Plot 1: Temperature evolution over time (heatmap)
    im = ax1.imshow(
        temp_field.T,
        extent=[0, time_array[-1], 0, x_coords[-1]],
        origin='lower',
        aspect='auto',
        cmap='hot'
    )
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Position (m)')
    ax1.set_title('Temperature Evolution')
    plt.colorbar(im, ax=ax1, label='Temperature (°C)')
    
    # Plot 2: Center temperature vs time
    ax2.plot(time_array, center_temp, 'b-', linewidth=2)
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Center Temperature (°C)')
    ax2.set_title('Center Temperature vs Time')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "simulation_results.png"), dpi=150, bbox_inches='tight')
    plt.close()
    
    # Create final temperature profile plot
    plt.figure(figsize=(8, 6))
    plt.plot(x_coords, temp_field[0, :], 'b-', label='Initial', linewidth=2)
    plt.plot(x_coords, temp_field[-1, :], 'r-', label='Final', linewidth=2)
    plt.xlabel('Position (m)')
    plt.ylabel('Temperature (°C)')
    plt.title('Temperature Profile: Initial vs Final')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join(output_dir, "temperature_profile.png"), dpi=150, bbox_inches='tight')
    plt.close()


def main():
    """Main simulation function"""
    
    parser = argparse.ArgumentParser(description="1D Heat Equation Simulation")
    parser.add_argument("--length", type=float, default=1.0, help="Rod length (m)")
    parser.add_argument("--time_steps", type=int, default=1000, help="Number of time steps")
    parser.add_argument("--spatial_steps", type=int, default=100, help="Number of spatial points")
    parser.add_argument("--diffusivity", type=float, default=0.01, help="Thermal diffusivity (m²/s)")
    parser.add_argument("--initial_temp", type=float, default=100.0, help="Initial center temperature (°C)")
    parser.add_argument("--boundary_temp", type=float, default=0.0, help="Boundary temperature (°C)")
    parser.add_argument("--end_time", type=float, default=1.0, help="Simulation end time (s)")
    parser.add_argument("--output_dir", type=str, default="/tmp/output", help="Output directory")
    
    args = parser.parse_args()
    
    print("Starting 1D Heat Equation Simulation")
    print(f"Parameters: length={args.length}, time_steps={args.time_steps}, diffusivity={args.diffusivity}")
    
    # Check for environment variables (from Docker container)
    job_id = os.getenv("JOB_ID", "local")
    output_dir = os.getenv("OUTPUT_DIR", args.output_dir)
    
    # Override parameters with environment variables if present
    params = {
        "length": float(os.getenv("PARAM_LENGTH", args.length)),
        "time_steps": int(os.getenv("PARAM_TIME_STEPS", args.time_steps)),
        "spatial_steps": int(os.getenv("PARAM_SPATIAL_STEPS", args.spatial_steps)),
        "diffusivity": float(os.getenv("PARAM_DIFFUSIVITY", args.diffusivity)),
        "initial_temp": float(os.getenv("PARAM_INITIAL_TEMP", args.initial_temp)),
        "boundary_temp": float(os.getenv("PARAM_BOUNDARY_TEMP", args.boundary_temp)),
        "end_time": float(os.getenv("PARAM_END_TIME", args.end_time)),
    }
    
    print(f"Job ID: {job_id}")
    print(f"Output directory: {output_dir}")
    print(f"Final parameters: {params}")
    
    try:
        # Run simulation
        results = solve_heat_equation(**params)
        
        # Save results
        save_results(results, output_dir)
        
        # Print summary
        stats = results["statistics"]
        print(f"\nSimulation completed successfully!")
        print(f"Max temperature: {stats['max_temperature']:.2f}°C")
        print(f"Final center temperature: {stats['center_temperature_final']:.2f}°C")
        print(f"Courant number: {results['parameters']['courant_number']:.3f}")
        
        return 0
        
    except Exception as e:
        print(f"ERROR: Simulation failed: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)