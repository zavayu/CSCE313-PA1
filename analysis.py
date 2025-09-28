#!/usr/bin/env python3
"""
Performance analysis script for measuring execution time of ./client -f {filename} [-m {value}]
"""

import subprocess
import time
import os
import sys
import glob
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import argparse

def measure_execution_time(command):
    """
    Measure the execution time of a command
    
    Args:
        command (list): Command to execute as a list of strings
    
    Returns:
        tuple: (execution_time_seconds, return_code, stdout, stderr)
    """
    start_time = time.time()
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60  # 60 second timeout
        )
        end_time = time.time()
        execution_time = end_time - start_time
        
        return execution_time, result.returncode, result.stdout, result.stderr
    
    except subprocess.TimeoutExpired:
        end_time = time.time()
        execution_time = end_time - start_time
        return execution_time, -1, "", "TIMEOUT"
    
    except Exception as e:
        end_time = time.time()
        execution_time = end_time - start_time
        return execution_time, -1, "", str(e)

def get_file_size(filepath):
    """Get file size in bytes"""
    try:
        return os.path.getsize(filepath)
    except OSError:
        return 0

def format_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0B"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}TB"

def create_performance_plot(results, output_filename="performance_plot.png"):
    """
    Create a plot of file size vs execution time for binary files
    
    Args:
        results (list): List of result dictionaries from performance analysis
        output_filename (str): Name of the output plot file
    """
    # Filter for binary files only
    bin_results = [r for r in results if r['filename'].endswith('.bin') and r['status'] == 'SUCCESS']
    
    if len(bin_results) < 2:
        print(f"Not enough binary file results ({len(bin_results)}) to create a meaningful plot")
        return
    
    # Extract data for plotting
    file_sizes_mb = [r['size_bytes'] / (1024 * 1024) for r in bin_results]  # Convert to MB
    exec_times = [r['time'] for r in bin_results]
    filenames = [r['filename'] for r in bin_results]
    
    # Create the plot
    plt.figure(figsize=(10, 6))
    
    # Scatter plot with points
    plt.scatter(file_sizes_mb, exec_times, color='blue', s=100, alpha=0.7, edgecolors='black')
    
    # Add labels for each point
    for i, filename in enumerate(filenames):
        plt.annotate(filename, (file_sizes_mb[i], exec_times[i]), 
                    textcoords="offset points", xytext=(0,10), ha='center', fontsize=9)
    
    # Add trend line
    if len(file_sizes_mb) > 1:
        z = np.polyfit(file_sizes_mb, exec_times, 1)
        p = np.poly1d(z)
        plt.plot(file_sizes_mb, p(file_sizes_mb), "r--", alpha=0.8, linewidth=2, 
                label=f'Trend line: y = {z[0]:.3f}x + {z[1]:.3f}')
        plt.legend()
    
    # Customize the plot
    plt.xlabel('File Size (MB)', fontsize=12)
    plt.ylabel('Execution Time (seconds)', fontsize=12)
    plt.title('File Size vs Execution Time for Binary Files', fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    
    # Add some statistics to the plot
    if len(bin_results) > 1:
        correlation = np.corrcoef(file_sizes_mb, exec_times)[0, 1]
        plt.text(0.02, 0.98, f'Correlation coefficient: {correlation:.3f}', 
                transform=plt.gca().transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Adjust layout and save
    plt.tight_layout()
    plt.savefig(output_filename, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"\nPerformance plot saved as '{output_filename}'")
    
    # Print some additional statistics
    if len(bin_results) > 1:
        print(f"Binary files analysis:")
        print(f"  Files plotted: {len(bin_results)}")
        print(f"  Size range: {min(file_sizes_mb):.1f} - {max(file_sizes_mb):.1f} MB")
        print(f"  Time range: {min(exec_times):.3f} - {max(exec_times):.3f} seconds")
        print(f"  Correlation coefficient: {correlation:.3f}")
        
        # Calculate throughput statistics
        throughputs = [size_mb / time for size_mb, time in zip(file_sizes_mb, exec_times)]
        avg_throughput = sum(throughputs) / len(throughputs)
        print(f"  Average throughput: {avg_throughput:.2f} MB/s")

def run_performance_analysis(m_value=None):
    """Run performance analysis on various test files"""
    
    # Check if client executable exists
    client_path = "./client"
    if not os.path.exists(client_path):
        print(f"Error: {client_path} not found. Make sure to build the client first.")
        return
    
    # Get test files from BIMDC directory
    test_files = []
    
    # Add CSV files (just the filenames, server will add BIMDC/ prefix)
    csv_files = glob.glob("BIMDC/*.csv")
    test_files.extend([os.path.basename(f) for f in csv_files])
    
    # Add binary test files (just the filenames, server will add BIMDC/ prefix)  
    bin_files = glob.glob("BIMDC/*.bin")
    test_files.extend([os.path.basename(f) for f in bin_files])
    
    # Sort files by size for better analysis
    test_files.sort(key=lambda x: get_file_size(os.path.join("BIMDC", x)))
    
    if not test_files:
        print("No test files found in BIMDC directory")
        return
    
    # Prepare command description for output
    cmd_desc = "./client -f {filename}"
    if m_value is not None:
        cmd_desc += f" -m {m_value}"
    
    print(f"Performance Analysis: {cmd_desc}")
    print("=" * 60)
    print(f"{'Filename':<25} {'Size':<10} {'Time (s)':<10} {'Status':<10}")
    print("-" * 60)
    
    results = []
    
    for test_file in test_files:
        filename = test_file  # Already just the basename
        file_path = os.path.join("BIMDC", test_file)  # Full path for size calculation
        file_size = get_file_size(file_path)
        
        # Run the command (client expects just the filename, server adds BIMDC/ prefix)
        command = [client_path, "-f", test_file]
        if m_value is not None:
            command.extend(["-m", str(m_value)])
        exec_time, return_code, stdout, stderr = measure_execution_time(command)
        
        # Determine status
        if return_code == 0:
            status = "SUCCESS"
        elif stderr == "TIMEOUT":
            status = "TIMEOUT"
        else:
            status = "ERROR"
        
        # Store results
        results.append({
            'filename': filename,
            'filepath': file_path,
            'size_bytes': file_size,
            'size_formatted': format_size(file_size),
            'time': exec_time,
            'status': status,
            'return_code': return_code,
            'stdout': stdout,
            'stderr': stderr
        })
        
        # Print result
        print(f"{filename:<25} {format_size(file_size):<10} {exec_time:<10.3f} {status:<10}")
    
    print("-" * 60)
    
    # Summary statistics
    successful_runs = [r for r in results if r['status'] == 'SUCCESS']
    
    if successful_runs:
        total_time = sum(r['time'] for r in successful_runs)
        avg_time = total_time / len(successful_runs)
        min_time = min(r['time'] for r in successful_runs)
        max_time = max(r['time'] for r in successful_runs)
        
        print(f"\nSummary (successful runs only):")
        print(f"  Total files tested: {len(test_files)}")
        print(f"  Successful runs: {len(successful_runs)}")
        print(f"  Failed runs: {len(test_files) - len(successful_runs)}")
        print(f"  Total execution time: {total_time:.3f} seconds")
        print(f"  Average execution time: {avg_time:.3f} seconds")
        print(f"  Fastest execution: {min_time:.3f} seconds")
        print(f"  Slowest execution: {max_time:.3f} seconds")
        
        # Performance vs file size analysis
        print(f"\nPerformance vs File Size Analysis:")
        for result in successful_runs:
            throughput = result['size_bytes'] / result['time'] / (1024 * 1024)  # MB/s
            print(f"  {result['filename']:<25} {throughput:.2f} MB/s")
    
    # Show errors if any
    failed_runs = [r for r in results if r['status'] != 'SUCCESS']
    if failed_runs:
        print(f"\nFailed Executions:")
        for result in failed_runs:
            print(f"  {result['filename']}: {result['status']}")
            if result['stderr'] and result['stderr'] != "TIMEOUT":
                print(f"    Error: {result['stderr']}")
    
    # Create performance plot for binary files
    create_performance_plot(results, "file_size_vs_time.png")
    
    return results

def test_single_file(filename, iterations=1, m_value=None):
    """Run test on a single file multiple times"""
    
    client_path = "./client"
    if not os.path.exists(client_path):
        print(f"Error: {client_path} not found. Make sure to build the client first.")
        return
    
    # Check if file exists (handle both full path and just filename)
    if os.path.exists(filename):
        # Full path provided
        test_filename = filename
        if filename.startswith("BIMDC/"):
            # Remove BIMDC/ prefix for client command
            client_filename = os.path.basename(filename)
        else:
            client_filename = filename
    elif os.path.exists(os.path.join("BIMDC", filename)):
        # Just filename provided, file exists in BIMDC
        test_filename = os.path.join("BIMDC", filename)
        client_filename = filename
    else:
        print(f"Error: File {filename} not found.")
        return
    
    print(f"Testing {test_filename} with {iterations} iteration(s)")
    print("=" * 50)
    
    times = []
    
    for i in range(iterations):
        command = [client_path, "-f", client_filename]
        if m_value is not None:
            command.extend(["-m", str(m_value)])
        exec_time, return_code, stdout, stderr = measure_execution_time(command)
        
        if return_code == 0:
            times.append(exec_time)
            print(f"Run {i+1}: {exec_time:.3f} seconds - SUCCESS")
        else:
            print(f"Run {i+1}: {exec_time:.3f} seconds - FAILED")
            if stderr:
                print(f"  Error: {stderr}")
    
    if times:
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"\nStatistics for {len(times)} successful runs:")
        print(f"  Average time: {avg_time:.3f} seconds")
        print(f"  Minimum time: {min_time:.3f} seconds")
        print(f"  Maximum time: {max_time:.3f} seconds")
        print(f"  Standard deviation: {(sum((t - avg_time)**2 for t in times) / len(times))**0.5:.3f} seconds")

def main():
    """Main function with command line argument handling"""
    
    parser = argparse.ArgumentParser(
        description='Performance analysis script for ./client',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''Examples:
  python3 analysis.py                     # Run full analysis on all files
  python3 analysis.py -m 256              # Run full analysis with -m 256
  python3 analysis.py -f test.bin         # Test single file once
  python3 analysis.py -f test.bin -i 5    # Test single file 5 times
  python3 analysis.py -f test.bin -m 512  # Test single file with -m 512
        '''
    )
    
    parser.add_argument('-m', '--buffer-size', type=int, metavar='VALUE',
                        help='Buffer size value to pass to client with -m flag')
    parser.add_argument('-f', '--file', type=str, metavar='FILENAME',
                        help='Test a single file instead of running full analysis')
    parser.add_argument('-i', '--iterations', type=int, default=1, metavar='N',
                        help='Number of iterations for single file testing (default: 1)')
    
    args = parser.parse_args()
    
    if args.file:
        # Test single file
        test_single_file(args.file, args.iterations, args.buffer_size)
    else:
        # Run full analysis
        run_performance_analysis(args.buffer_size)

if __name__ == "__main__":
    main()