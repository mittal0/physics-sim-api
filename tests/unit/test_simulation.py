import os
import tempfile
from unittest.mock import Mock, patch

import numpy as np
import pytest

from sim.run_sim import solve_heat_equation, save_results, create_plots


class TestSimulation:
    """Test the physics simulation functionality"""

    def test_solve_heat_equation_basic(self):
        """Test basic heat equation solving"""
        result = solve_heat_equation(
            length=1.0,
            time_steps=10,
            spatial_steps=20,
            diffusivity=0.01,
            initial_temp=100.0,
            boundary_temp=0.0,
            end_time=0.1,
        )
        
        # Check return structure
        assert "temperature_field" in result
        assert "x_coordinates" in result
        assert "time_array" in result
        assert "parameters" in result
        assert "statistics" in result
        assert "center_temperature_history" in result
        
        # Check dimensions
        temp_field = result["temperature_field"]
        assert temp_field.shape == (11, 20)  # time_steps + 1, spatial_steps
        
        # Check that temperature decreases over time (heat dissipation)
        center_temp = result["center_temperature_history"]
        assert center_temp[0] > center_temp[-1]  # Should cool down
        
        # Check boundary conditions
        assert np.allclose(temp_field[:, 0], 0.0)  # Left boundary
        assert np.allclose(temp_field[:, -1], 0.0)  # Right boundary

    def test_solve_heat_equation_stability_warning(self, capsys):
        """Test stability warning for high Courant number"""
        solve_heat_equation(
            length=1.0,
            time_steps=10,
            spatial_steps=10,
            diffusivity=1.0,  # High diffusivity
            end_time=1.0,
        )
        
        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "Courant number" in captured.out

    def test_solve_heat_equation_parameters(self):
        """Test parameter validation and storage"""
        params = {
            "length": 2.0,
            "time_steps": 50,
            "spatial_steps": 30,
            "diffusivity": 0.05,
            "initial_temp": 200.0,
            "boundary_temp": 25.0,
            "end_time": 0.5,
        }
        
        result = solve_heat_equation(**params)
        
        # Check that parameters are stored correctly
        stored_params = result["parameters"]
        for key, value in params.items():
            assert stored_params[key] == value
        
        # Check calculated parameters
        assert "dx" in stored_params
        assert "dt" in stored_params
        assert "courant_number" in stored_params

    def test_solve_heat_equation_statistics(self):
        """Test that statistics are calculated correctly"""
        result = solve_heat_equation(
            length=1.0,
            time_steps=20,
            spatial_steps=30,
            diffusivity=0.01,
            initial_temp=150.0,
            boundary_temp=10.0,
            end_time=0.2,
        )
        
        stats = result["statistics"]
        temp_field = result["temperature_field"]
        
        # Check statistics
        assert stats["max_temperature"] == np.max(temp_field)
        assert stats["min_temperature"] == np.min(temp_field)
        assert stats["final_max_temperature"] == np.max(temp_field[-1, :])
        
        # Check that final center temperature is reasonable
        assert 0 <= stats["center_temperature_final"] <= stats["max_temperature"]

    def test_save_results(self):
        """Test saving simulation results"""
        # Generate test results
        result = solve_heat_equation(
            length=1.0,
            time_steps=5,
            spatial_steps=10,
            diffusivity=0.01,
            end_time=0.1,
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            save_results(result, temp_dir)
            
            # Check that files were created
            expected_files = [
                "meta.json",
                "result.csv",
                "temperature_field.npy",
                "x_coordinates.npy",
                "time_array.npy",
                "simulation_results.png",
                "temperature_profile.png",
            ]
            
            for filename in expected_files:
                filepath = os.path.join(temp_dir, filename)
                assert os.path.exists(filepath), f"File {filename} was not created"
            
            # Check metadata file content
            import json
            with open(os.path.join(temp_dir, "meta.json"), "r") as f:
                metadata = json.load(f)
            
            assert metadata["simulation_type"] == "1D_heat_equation"
            assert "timestamp" in metadata
            assert "parameters" in metadata
            assert "statistics" in metadata
            
            # Check CSV file
            csv_path = os.path.join(temp_dir, "result.csv")
            data = np.loadtxt(csv_path, delimiter=",", skiprows=1)
            assert data.shape[1] == 2  # time, temperature
            assert data.shape[0] == 6  # time_steps + 1

    def test_create_plots(self):
        """Test plot creation"""
        # Generate test results
        result = solve_heat_equation(
            length=1.0,
            time_steps=5,
            spatial_steps=10,
            diffusivity=0.01,
            end_time=0.1,
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock matplotlib to avoid display issues
            with patch('matplotlib.pyplot.savefig') as mock_savefig:
                create_plots(result, temp_dir)
                
                # Check that savefig was called for both plots
                assert mock_savefig.call_count == 2
                
                # Check that the correct filenames were used
                call_args = [call[0][0] for call in mock_savefig.call_args_list]
                expected_files = [
                    os.path.join(temp_dir, "simulation_results.png"),
                    os.path.join(temp_dir, "temperature_profile.png"),
                ]
                
                for expected_file in expected_files:
                    assert expected_file in call_args

    def test_simulation_deterministic(self):
        """Test that simulation is deterministic"""
        params = {
            "length": 1.0,
            "time_steps": 20,
            "spatial_steps": 30,
            "diffusivity": 0.01,
            "initial_temp": 100.0,
            "boundary_temp": 0.0,
            "end_time": 0.2,
        }
        
        # Run simulation twice
        result1 = solve_heat_equation(**params)
        result2 = solve_heat_equation(**params)
        
        # Results should be identical
        np.testing.assert_array_equal(
            result1["temperature_field"],
            result2["temperature_field"]
        )
        
        assert result1["statistics"] == result2["statistics"]

    def test_simulation_energy_conservation(self):
        """Test basic energy conservation principles"""
        result = solve_heat_equation(
            length=1.0,
            time_steps=100,
            spatial_steps=50,
            diffusivity=0.01,
            initial_temp=100.0,
            boundary_temp=0.0,
            end_time=1.0,
        )
        
        temp_field = result["temperature_field"]
        
        # Total energy should decrease over time (cooling)
        initial_energy = np.sum(temp_field[0, :])
        final_energy = np.sum(temp_field[-1, :])
        
        assert final_energy < initial_energy
        
        # All temperatures should be non-negative
        assert np.all(temp_field >= 0)
        
        # Maximum temperature should not exceed initial temperature
        assert np.max(temp_field) <= 100.0