import streamlit as st 
import socket
from threading import Thread, Lock
from queue import Queue
from time import time

# Thread-safe queue to store open ports
open_ports = Queue()

def prepare_ports(start: int, end: int):
    """Generator function to yield ports in the range."""
    for port in range(start, end + 1):
        yield port

def scan_port(ip, timeout, port_queue, result_queue, lock, total_ports):
    """Scan ports using the provided generator."""
    scanned_ports = 0
    while not port_queue.empty():
        try:
            port = port_queue.get()
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)  # Set socket timeout
                s.connect((ip, port))  # Try to connect to the IP on the current port
                with lock:  # Thread-safe addition to the result queue
                    result_queue.put(port)
        except (ConnectionRefusedError, socket.timeout):
            pass
        except Exception as e:
            st.error(f"Error scanning port {port}: {e}")
        finally:
            scanned_ports += 1
            # Update session state for progress
            st.session_state.scanned_ports = scanned_ports
            port_queue.task_done()  # Mark the port as processed

def prepare_threads(ip, timeout, threads, port_queue, result_queue, total_ports):
    """Create, start, and join threads to scan ports concurrently."""
    lock = Lock()
    thread_list = []
    for _ in range(threads):
        thread = Thread(target=scan_port, args=(ip, timeout, port_queue, result_queue, lock, total_ports))
        thread_list.append(thread)

    # Start all threads
    for thread in thread_list:
        thread.start()

    # Join all threads
    for thread in thread_list:
        thread.join()

# Streamlit UI
st.title("Python-Based Fast Port Scanner")
st.write("A simple port scanner built with Python and Streamlit.")

# Input fields
ip = st.text_input("Enter the IP address to scan (e.g., 192.168.1.1):", "")
start_port = st.number_input("Start Port:", min_value=1, max_value=65535, value=1, step=1)
end_port = st.number_input("End Port:", min_value=1, max_value=65535, value=1024, step=1)
threads = st.slider("Number of Threads:", min_value=1, max_value=1000, value=100, step=10)
timeout = st.slider("Socket Timeout (seconds):", min_value=0.1, max_value=10.0, value=1.0, step=0.1)

# Initialize session state for progress tracking
if 'scanned_ports' not in st.session_state:
    st.session_state.scanned_ports = 0

if st.button("Start Scan"):
    if ip.strip() == "":
        st.error("Please enter a valid IP address.")
    elif start_port > end_port:
        st.error("Start port must be less than or equal to end port.")
    else:
        # Initialize port queues and results
        port_queue = Queue()
        result_queue = Queue()

        for port in prepare_ports(start_port, end_port):
            port_queue.put(port)

        total_ports = end_port - start_port + 1
        progress_bar = st.progress(0)
        
        st.write("Starting scan...")
        start_time = time()

        # Run the port scan in separate threads
        prepare_threads(ip, timeout, threads, port_queue, result_queue, total_ports)

        end_time = time()

        # Collect results
        open_ports_list = []
        while not result_queue.empty():
            open_ports_list.append(result_queue.get())

        # Display results
        if open_ports_list:
            st.success(f"Open Ports Found: {sorted(open_ports_list)}")
        else:
            st.info("No open ports found.")

        st.write(f"Time Taken: {round(end_time - start_time, 2)} seconds")
        progress_bar.progress(st.session_state.scanned_ports / total_ports)
