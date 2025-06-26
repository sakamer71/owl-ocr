#!/usr/bin/env python3
"""
Owl OCR Streamlit Frontend

A Streamlit-based frontend for the Owl OCR API that allows users to:
- Upload files for OCR processing
- Monitor job status
- View extracted text, tables, and images
"""

import os
import time
import tempfile
import json
from pathlib import Path
from typing import Dict, List, Optional, Union

import streamlit as st
import httpx
import base64
from PIL import Image

# API Configuration
API_URL = "http://localhost:8000"  # Change if your API is running elsewhere

# Page setup
st.set_page_config(
    page_title="Owl OCR",
    page_icon="🦉",
    layout="wide",
)

# Functions for API communication
def api_upload_file(file_obj):
    """Upload a file to the API for processing."""
    if not file_obj:
        return None, "No file selected"
    
    try:
        # Create files dictionary for API request
        files = {"file": (file_obj.name, file_obj, file_obj.type)}
        
        with st.spinner("Uploading file..."):
            with httpx.Client() as client:
                response = client.post(
                    f"{API_URL}/api/process", 
                    files=files,
                    timeout=60.0  # Long timeout for large files
                )
        
        if response.status_code == 200:
            return response.json(), None
        else:
            error_detail = response.json().get("detail", "Unknown error")
            return None, f"API error: {response.status_code} - {error_detail}"
        
    except Exception as e:
        return None, f"Error uploading file: {str(e)}"

def api_get_job_status(job_id):
    """Get job status from the API."""
    if not job_id:
        return None, "No job ID provided"
    
    try:
        with httpx.Client() as client:
            response = client.get(f"{API_URL}/api/jobs/{job_id}")
        
        if response.status_code == 200:
            return response.json(), None
        else:
            error_detail = response.json().get("detail", "Unknown error")
            return None, f"API error: {response.status_code} - {error_detail}"
        
    except Exception as e:
        return None, f"Error getting job status: {str(e)}"

def api_get_job_result(job_id):
    """Get job result from the API."""
    if not job_id:
        return None, "No job ID provided"
    
    try:
        with httpx.Client() as client:
            response = client.get(f"{API_URL}/api/jobs/{job_id}/result")
        
        if response.status_code == 200:
            return response.json(), None
        else:
            error_detail = response.json().get("detail", "Unknown error")
            return None, f"API error: {response.status_code} - {error_detail}"
        
    except Exception as e:
        return None, f"Error getting job result: {str(e)}"

def get_image_as_base64(image_path):
    """Convert an image file to base64 for display in HTML."""
    try:
        if not os.path.exists(image_path):
            return None
        
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")
    except Exception:
        return None

# Session state initialization
if "page" not in st.session_state:
    st.session_state.page = "upload"

if "job_id" not in st.session_state:
    st.session_state.job_id = None

if "job_status" not in st.session_state:
    st.session_state.job_status = None

if "job_result" not in st.session_state:
    st.session_state.job_result = None

if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = True

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = 0

# Helper functions for navigation
def go_to_upload():
    st.session_state.page = "upload"
    st.session_state.job_id = None
    st.session_state.job_status = None
    st.session_state.job_result = None

def go_to_status(job_id):
    st.session_state.page = "status"
    st.session_state.job_id = job_id

def go_to_results():
    st.session_state.page = "results"

def refresh_job_status():
    if st.session_state.job_id:
        job_status, error = api_get_job_status(st.session_state.job_id)
        if job_status:
            st.session_state.job_status = job_status
            if job_status["status"] == "completed":
                # Get results if job is completed
                job_result, result_error = api_get_job_result(st.session_state.job_id)
                if job_result:
                    st.session_state.job_result = job_result
                    return True
        return False
    return False

# Header
st.title("🦉 Owl OCR")
st.markdown("Extract text and content from images, PDFs, and PowerPoint files")
st.divider()

# Auto-refresh job status
current_time = time.time()
if (st.session_state.auto_refresh and 
    st.session_state.page == "status" and 
    st.session_state.job_id and 
    current_time - st.session_state.last_refresh > 2):  # Refresh every 2 seconds
    
    st.session_state.last_refresh = current_time
    job_completed = refresh_job_status()
    
    # Auto-navigate to results if job completed
    if job_completed:
        st.session_state.page = "results"

# Page: File Upload
if st.session_state.page == "upload":
    st.header("Upload File for OCR Processing")
    
    uploaded_file = st.file_uploader(
        "Select a file to process",
        type=["png", "jpg", "jpeg", "pdf", "pptx", "ppt"]
    )
    
    if uploaded_file is not None:
        st.write(f"Selected file: {uploaded_file.name}")
        st.write(f"File type: {uploaded_file.type}")
        st.write(f"File size: {uploaded_file.size} bytes")
        
        if st.button("Process File", type="primary"):
            job_data, error = api_upload_file(uploaded_file)
            
            if error:
                st.error(error)
            elif job_data:
                st.session_state.job_id = job_data["job_id"]
                st.session_state.job_status = job_data
                go_to_status(job_data["job_id"])
                st.rerun()

# Page: Job Status
elif st.session_state.page == "status":
    st.header("Job Status")
    
    if not st.session_state.job_id:
        st.error("No active job")
        st.button("Back to Upload", on_click=go_to_upload)
    else:
        job_status = st.session_state.job_status
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Job ID:** {job_status['job_id']}")
            st.write(f"**File:** {job_status['file_name']}")
            st.write(f"**Status:** {job_status['status']}")
            st.write(f"**Progress:** {job_status.get('progress', 0)}%")
            
            if job_status.get('message'):
                st.write(f"**Message:** {job_status['message']}")
        
        with col2:
            st.write(f"**Created:** {job_status['created_at']}")
            st.write(f"**Updated:** {job_status['updated_at']}")
        
        st.progress(job_status.get('progress', 0) / 100.0)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.checkbox("Auto-refresh", value=st.session_state.auto_refresh, 
                      key="auto_refresh")
        
        with col2:
            if st.button("Refresh Status"):
                refresh_job_status()
                st.rerun()
        
        if job_status["status"] == "completed":
            with col3:
                if st.button("View Results", type="primary"):
                    job_result, error = api_get_job_result(st.session_state.job_id)
                    if error:
                        st.error(error)
                    else:
                        st.session_state.job_result = job_result
                        go_to_results()
                        st.rerun()
        
        st.button("Back to Upload", on_click=go_to_upload)

# Page: Results
elif st.session_state.page == "results":
    st.header("OCR Results")
    
    if not st.session_state.job_result:
        job_result, error = api_get_job_result(st.session_state.job_id)
        if error:
            st.error(error)
            st.button("Back to Status", on_click=lambda: go_to_status(st.session_state.job_id))
            st.button("Back to Upload", on_click=go_to_upload)
        else:
            st.session_state.job_result = job_result
            st.rerun()
    else:
        job_result = st.session_state.job_result
        
        st.write(f"**File:** {job_result['file_name']}")
        st.write(f"**File Type:** {job_result['file_type']}")
        
        tab1, tab2, tab3 = st.tabs(["Extracted Text", "Tables", "Images"])
        
        # Tab: Extracted Text
        with tab1:
            if job_result.get('texts') and len(job_result['texts']) > 0:
                for i, text in enumerate(job_result['texts']):
                    with st.expander(f"Text from {text['source']} {text.get('page_number', '')}", expanded=i==0):
                        st.text_area(
                            "Extracted text", 
                            value=text['text'],
                            height=300,
                            key=f"text_{i}"
                        )
                        st.button("Copy", key=f"copy_{i}", use_container_width=True)
            else:
                st.info("No text content found")
        
        # Tab: Tables
        with tab2:
            if job_result.get('tables') and len(job_result['tables']) > 0:
                for i, table in enumerate(job_result['tables']):
                    with st.expander(f"Table from {table['source']} {table.get('page_number', '')}", expanded=i==0):
                        st.components.v1.html(table['html'], height=300)
            else:
                st.info("No table content found")
        
        # Tab: Images
        with tab3:
            if job_result.get('images') and len(job_result['images']) > 0:
                cols = st.columns(3)
                for i, img in enumerate(job_result['images']):
                    with cols[i % 3]:
                        source_label = f"{img['source']} {img.get('page_number', '')}"
                        try:
                            # Try to open image from path
                            image = Image.open(img['path'])
                            st.image(image, caption=source_label)
                        except Exception:
                            # Fallback if direct opening fails
                            base64_img = get_image_as_base64(img['path'])
                            if base64_img:
                                st.markdown(f"""
                                <div style="text-align: center;">
                                    <img src="data:image/png;base64,{base64_img}" style="max-width: 100%;">
                                    <p>{source_label}</p>
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                st.error(f"Could not load image: {img['path']}")
            else:
                st.info("No images found")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.button("Back to Status", on_click=lambda: go_to_status(st.session_state.job_id))
        
        with col2:
            st.button("Back to Upload", on_click=go_to_upload)

# Footer
st.divider()
st.markdown("""
<div style="text-align: center;">
    <p>© 2025 Owl OCR | <a href="{}/docs" target="_blank">API Documentation</a></p>
</div>
""".format(API_URL), unsafe_allow_html=True)