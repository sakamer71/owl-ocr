#!/usr/bin/env python3
"""
Owl OCR GUI Frontend

A FastGui-based frontend for the Owl OCR API that allows users to:
- Upload files for OCR processing
- Monitor job status
- View extracted text, tables, and images
"""

import os
import time
from typing import Dict, List, Optional, Union
import base64
from pathlib import Path
import tempfile

import fastgui as fg
import httpx

# API Configuration
API_URL = "http://localhost:8000"  # Change this if your API is running on a different host/port

# FastGui app state
class AppState(fg.State):
    # Upload state
    uploaded_file: Optional[str] = None
    file_content: Optional[bytes] = None
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    
    # Job state
    job_id: Optional[str] = None
    job_status: Optional[str] = None
    job_progress: int = 0
    job_message: Optional[str] = None
    job_created_at: Optional[str] = None
    job_updated_at: Optional[str] = None
    
    # Result state
    texts: List[Dict] = []
    tables: List[Dict] = []
    images: List[Dict] = []
    
    # UI state
    loading: bool = False
    error: Optional[str] = None
    current_tab: str = "upload"
    result_tab: str = "text"
    
    # Auto-refresh timer
    last_refresh: float = 0
    auto_refresh: bool = True

# Create FastGui app
app = fg.App(
    title="Owl OCR Frontend",
    state=AppState(),
    css="static/style.css",  # Add CSS styling
)

# API communication helpers
async def api_upload_file(state: AppState) -> Union[Dict, str]:
    """Upload a file to the API for processing."""
    state.loading = True
    state.error = None
    
    try:
        # Create temporary file from uploaded content
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(state.file_content)
            tmp_path = tmp.name
        
        # Upload file to API
        files = {"file": (state.file_name, open(tmp_path, "rb"), "application/octet-stream")}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_URL}/api/process",
                files=files,
                timeout=60.0  # Long timeout for large files
            )
        
        # Clean up temporary file
        os.unlink(tmp_path)
        
        # Check response
        if response.status_code == 200:
            result = response.json()
            state.job_id = result["job_id"]
            state.job_status = result["status"]
            state.job_progress = result.get("progress", 0)
            state.job_message = result.get("message")
            state.job_created_at = result["created_at"]
            state.job_updated_at = result["updated_at"]
            state.current_tab = "status"
            return result
        else:
            error_detail = response.json().get("detail", "Unknown error")
            state.error = f"API error: {response.status_code} - {error_detail}"
            return f"Error: {error_detail}"
    
    except Exception as e:
        state.error = f"Error uploading file: {str(e)}"
        return f"Error: {str(e)}"
    
    finally:
        state.loading = False

async def api_get_job_status(state: AppState) -> Union[Dict, str]:
    """Get job status from the API."""
    if not state.job_id:
        state.error = "No active job"
        return "Error: No active job"
    
    state.loading = True
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/api/jobs/{state.job_id}")
        
        if response.status_code == 200:
            result = response.json()
            state.job_status = result["status"]
            state.job_progress = result.get("progress", 0)
            state.job_message = result.get("message")
            state.job_updated_at = result["updated_at"]
            
            # If job is completed, allow viewing results
            if state.job_status == "completed":
                await api_get_job_result(state)
            
            return result
        else:
            error_detail = response.json().get("detail", "Unknown error")
            state.error = f"API error: {response.status_code} - {error_detail}"
            return f"Error: {error_detail}"
    
    except Exception as e:
        state.error = f"Error getting job status: {str(e)}"
        return f"Error: {str(e)}"
    
    finally:
        state.loading = False

async def api_get_job_result(state: AppState) -> Union[Dict, str]:
    """Get job result from the API."""
    if not state.job_id:
        state.error = "No active job"
        return "Error: No active job"
    
    if state.job_status != "completed":
        state.error = "Job is not completed yet"
        return "Error: Job is not completed yet"
    
    state.loading = True
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/api/jobs/{state.job_id}/result")
        
        if response.status_code == 200:
            result = response.json()
            state.texts = result.get("texts", [])
            state.tables = result.get("tables", [])
            state.images = result.get("images", [])
            state.current_tab = "result"
            return result
        else:
            error_detail = response.json().get("detail", "Unknown error")
            state.error = f"API error: {response.status_code} - {error_detail}"
            return f"Error: {error_detail}"
    
    except Exception as e:
        state.error = f"Error getting job result: {str(e)}"
        return f"Error: {str(e)}"
    
    finally:
        state.loading = False

# File upload handlers
def on_file_selected(state: AppState, evt: fg.UploadEvent):
    """Handle file selection event."""
    if evt.content:
        state.uploaded_file = evt.name
        state.file_content = evt.content
        state.file_name = evt.name
        state.file_size = len(evt.content)
        state.file_type = Path(evt.name).suffix.lower()[1:]  # Remove the dot
        state.error = None
    else:
        state.uploaded_file = None
        state.file_content = None
        state.file_name = None
        state.file_size = None
        state.file_type = None

# Auto-refresh handler
async def check_job_status(state: AppState):
    """Periodically check job status if auto-refresh is enabled."""
    if not state.auto_refresh or not state.job_id or state.job_status == "completed" or state.job_status == "failed":
        return
    
    current_time = time.time()
    if current_time - state.last_refresh >= 2.0:  # Check every 2 seconds
        state.last_refresh = current_time
        await api_get_job_status(state)

# UI Components
def file_upload_panel(state: AppState) -> fg.Component:
    """File upload panel component."""
    return fg.Stack([
        fg.Heading(3, "Upload File for OCR Processing"),
        
        fg.Text("Select a file to process:"),
        fg.Upload(on_selected=on_file_selected),
        
        fg.Divider(),
        
        fg.Conditional(
            state.uploaded_file is not None,
            fg.Stack([
                fg.Text(f"Selected file: {state.file_name}"),
                fg.Text(f"File size: {state.file_size} bytes"),
                fg.Text(f"File type: {state.file_type}"),
                
                fg.Divider(),
                
                fg.Button(
                    "Process File", 
                    on_click=lambda: app.run_async(api_upload_file, state),
                    style={"background-color": "#4CAF50", "color": "white"}
                ),
            ]),
            fg.Text("No file selected")
        ),
        
        fg.Conditional(
            state.loading,
            fg.Text("Uploading file...", style={"color": "blue"})
        ),
        
        fg.Conditional(
            state.error is not None,
            fg.Text(lambda s: s.error, style={"color": "red"})
        )
    ])

def job_status_panel(state: AppState) -> fg.Component:
    """Job status panel component."""
    return fg.Stack([
        fg.Heading(3, "Job Status"),
        
        fg.Conditional(
            state.job_id is not None,
            fg.Stack([
                fg.Text(f"Job ID: {state.job_id}"),
                fg.Text(f"File: {state.file_name}"),
                fg.Text(f"Status: {state.job_status}"),
                fg.Text(f"Progress: {state.job_progress}%"),
                
                fg.ProgressBar(lambda s: s.job_progress / 100),
                
                fg.Conditional(
                    state.job_message is not None,
                    fg.Text(f"Message: {state.job_message}")
                ),
                
                fg.Divider(),
                
                fg.Stack([
                    fg.Text("Auto-refresh:"),
                    fg.Switch(
                        checked=lambda s: s.auto_refresh,
                        on_change=lambda s, e: setattr(s, "auto_refresh", e.checked),
                        style={"margin-left": "10px"}
                    )
                ], direction="horizontal"),
                
                fg.Button(
                    "Refresh Status", 
                    on_click=lambda: app.run_async(api_get_job_status, state)
                ),
                
                fg.Conditional(
                    state.job_status == "completed",
                    fg.Button(
                        "View Results", 
                        on_click=lambda s: setattr(s, "current_tab", "result"),
                        style={"background-color": "#2196F3", "color": "white"}
                    )
                ),
                
                fg.Button(
                    "Back to Upload", 
                    on_click=lambda s: setattr(s, "current_tab", "upload")
                ),
                
                fg.Divider(),
                
                fg.Text(f"Created: {state.job_created_at}"),
                fg.Text(f"Updated: {state.job_updated_at}")
            ]),
            fg.Stack([
                fg.Text("No active job"),
                fg.Button(
                    "Back to Upload", 
                    on_click=lambda s: setattr(s, "current_tab", "upload")
                )
            ])
        ),
        
        fg.Conditional(
            state.loading,
            fg.Text("Loading...", style={"color": "blue"})
        ),
        
        fg.Conditional(
            state.error is not None,
            fg.Text(lambda s: s.error, style={"color": "red"})
        )
    ])

def results_panel(state: AppState) -> fg.Component:
    """Results panel component."""
    return fg.Stack([
        fg.Heading(3, "OCR Results"),
        
        fg.Conditional(
            state.job_id is not None and state.job_status == "completed",
            fg.Stack([
                fg.Tabs(
                    tabs=[
                        fg.Tab("Text", "text"),
                        fg.Tab("Tables", "tables"),
                        fg.Tab("Images", "images")
                    ],
                    selected=lambda s: s.result_tab,
                    on_change=lambda s, e: setattr(s, "result_tab", e.selected)
                ),
                
                fg.Divider(),
                
                # Text results tab
                fg.Conditional(
                    state.result_tab == "text",
                    fg.Stack([
                        fg.Conditional(
                            len(state.texts) > 0,
                            fg.Stack([
                                fg.Heading(4, "Extracted Text"),
                                *[fg.Stack([
                                    fg.Heading(5, f"Text from {text['source']} {text['page_number'] if text['page_number'] is not None else ''}"),
                                    fg.Code(text["text"])
                                ]) for text in state.texts]
                            ]),
                            fg.Text("No text content found")
                        )
                    ])
                ),
                
                # Tables results tab
                fg.Conditional(
                    state.result_tab == "tables",
                    fg.Stack([
                        fg.Conditional(
                            len(state.tables) > 0,
                            fg.Stack([
                                fg.Heading(4, "Extracted Tables"),
                                *[fg.Stack([
                                    fg.Heading(5, f"Table from {table['source']} {table['page_number'] if table['page_number'] is not None else ''}"),
                                    fg.HTML(table["html"])
                                ]) for table in state.tables]
                            ]),
                            fg.Text("No table content found")
                        )
                    ])
                ),
                
                # Images results tab
                fg.Conditional(
                    state.result_tab == "images",
                    fg.Stack([
                        fg.Conditional(
                            len(state.images) > 0,
                            fg.Stack([
                                fg.Heading(4, "Extracted Images"),
                                fg.Grid(
                                    [fg.Stack([
                                        fg.Image(
                                            # Use direct file path for images
                                            src=f"file://{image['path']}",
                                            style={"max-width": "300px", "max-height": "300px"}
                                        ),
                                        fg.Text(f"From {image['source']} {image['page_number'] if image['page_number'] is not None else ''}")
                                    ]) for image in state.images],
                                    columns=3
                                )
                            ]),
                            fg.Text("No image content found")
                        )
                    ])
                ),
                
                fg.Divider(),
                
                fg.Button(
                    "Back to Status", 
                    on_click=lambda s: setattr(s, "current_tab", "status")
                ),
                
                fg.Button(
                    "Back to Upload", 
                    on_click=lambda s: setattr(s, "current_tab", "upload")
                )
            ]),
            fg.Stack([
                fg.Text("No completed job results available"),
                fg.Button(
                    "Back to Status", 
                    on_click=lambda s: setattr(s, "current_tab", "status")
                ),
                fg.Button(
                    "Back to Upload", 
                    on_click=lambda s: setattr(s, "current_tab", "upload")
                )
            ])
        ),
        
        fg.Conditional(
            state.loading,
            fg.Text("Loading results...", style={"color": "blue"})
        ),
        
        fg.Conditional(
            state.error is not None,
            fg.Text(lambda s: s.error, style={"color": "red"})
        )
    ])

# Main App Component
@app.component
def app_component(state: AppState) -> fg.Component:
    app.run_async(check_job_status, state)
    
    return fg.Stack([
        fg.Stack([
            fg.Heading(1, "Owl OCR"),
            fg.Text("Extract text and content from images, PDFs, and PowerPoint files")
        ], align="center"),
        
        fg.Divider(),
        
        fg.Conditional(state.current_tab == "upload", file_upload_panel(state)),
        fg.Conditional(state.current_tab == "status", job_status_panel(state)),
        fg.Conditional(state.current_tab == "result", results_panel(state)),
        
        fg.Divider(),
        
        fg.Stack([
            fg.Text("© 2025 Owl OCR"),
            fg.Link("API Documentation", f"{API_URL}/docs")
        ], align="center")
    ])

if __name__ == "__main__":
    app.run(port=8050)  # Run on a different port than the API