import os
import socket
import time
from threading import Thread
from http.server import HTTPServer, SimpleHTTPRequestHandler
from weasyprint import HTML
from datetime import datetime


def create_html(
    fromdate,
    todate,
    correlations,
    lag_plots,
    include_heatmap=True,
    include_scatter=True,
    include_lag_plots=True,
    include_details=True,
):
    html_content = f"""
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Correlation Analysis Report</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Slab:wght@100..900&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Poppins:ital,wght@0,100;0,200;0,300;0,400;0,500;0,600;0,700;0,800;0,900&display=swap');
        
        @page {{
            size: A4;
            margin: 20mm;
        }}
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            box-sizing: border-box;
            font-size: 10pt;
            line-height: 1.5;
        }}
        .header {{
            text-align: center;
            margin-bottom: 20px;
        }}
        .header h1 {{
            font-family: 'Poppins', sans-serif;
            font-size: 24pt;
            margin: 0;
        }}
        .header p {{
            font-family: 'Roboto Slab', serif;
            font-size: 12pt;
            margin: 0;
        }}
        .section {{
            margin-bottom: 20px;
        }}
        .section h2 {{
            font-family: 'Poppins', sans-serif;
            font-size: 18pt;
            margin-bottom: 10px;
        }}
        .section p {{
            font-family: 'Roboto Slab', serif;
            font-size: 10pt;
            margin-bottom: 10px;
        }}
        .image-container {{
            text-align: center;
            margin-bottom: 20px;
        }}
        .image-container img {{
            max-width: 100%;
            height: auto;
        }}
    </style>
</head>

<body>
    <div class="header">
        <h1>Correlation Analysis Report</h1>
        <p> Data is analyzed</p>
        
       <p>from Date: {fromdate.strftime('%d %B %Y')} to Date: {todate.strftime('%d %B %Y')}</p>
        <p>created at Date: {datetime.now().strftime('%d %B %Y')}</p>
    </div>
    
    {"<div class='section'><h2> Best Correlation Heatmap</h2><div class='image-container'><img src='http://localhost:8000/heatmap.png' alt='Best Correlation Heatmap'></div></div>" if include_heatmap else ""}
    
    {"<div class='section'><h2> In-Depth Scatter Plot</h2><div class='image-container'><img src='http://localhost:8000/in_depth_scatter.png' alt='In-Depth Scatter Plot'></div></div>" if include_scatter else ""}
    
    {"<div class='section'><h2> Lag Correlation Plots</h2>" + ''.join(f"<div class='image-container'><img src='http://localhost:8000/lag_plots/{os.path.basename(filename)}' alt='{os.path.basename(filename)}'></div>" for filename in lag_plots) + "</div>" if include_lag_plots else ""}
    
    {"<div class='section'><h2> Correlation Details</h2><p>The following table provides detailed correlation values for each pair of columns analyzed:</p><table border='1' cellspacing='0' cellpadding='5'><thead><tr><th>Column Pair</th><th>Best Correlation</th><th>Best Lag</th><th>Lag Unit</th></tr></thead><tbody>" + ''.join(f"<tr><td>{pair}</td><td>{info['best_correlation']}</td><td>{info['best_lag']}</td><td>{info['lag_unit']}</td></tr>" for pair, info in correlations.items()) + "</tbody></table></div>" if include_details else ""}
</body>

</html>
"""
    return html_content


def create_pdf(
    fromdate,
    todate,
    file_path,
    correlations,
    include_heatmap=True,
    include_scatter=True,
    include_lag_plots=True,
    include_details=True,
    lag_plots=[],
):
    print("Generating PDF report...")

    # Create HTML content
    html_content = create_html(
        fromdate,
        todate,
        correlations,
        lag_plots,
        include_heatmap,
        include_scatter,
        include_lag_plots,
        include_details,
    )

    # Save the HTML content to a local file in /tmp
    html_file_path = "/tmp/report.html"
    with open(html_file_path, "w", encoding="utf-8") as html_file:
        html_file.write(html_content)

    # Define the handler and server
    class SilentHTTPRequestHandler(SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # Silence the logging

    def start_server():
        os.chdir("/tmp")
        httpd = HTTPServer(("localhost", 8000), SilentHTTPRequestHandler)
        # Store the server object so it can be shut down later
        server_info["httpd"] = httpd
        httpd.serve_forever()

    server_info = {}
    server_thread = Thread(target=start_server)
    server_thread.daemon = True
    server_thread.start()

    # Wait for the server to start
    for _ in range(10):  # Retry up to 10 times
        try:
            with socket.create_connection(("localhost", 8000), timeout=2):
                break  # Connection successful, proceed with PDF generation
        except (ConnectionRefusedError, OSError):
            time.sleep(0.5)
            print("Waiting for server to start...")
    else:
        print("Failed to start server.")
        return

    # Generate PDF with WeasyPrint with custom headers
    try:
        HTML("http://localhost:8000/report.html").write_pdf(file_path)
        print("PDF file generated successfully.")
    except Exception as e:
        print(f"Error generating PDF: {e}")
    finally:
        # Shutdown the server after the work is done
        if "httpd" in server_info:
            server_info["httpd"].shutdown()
            server_info["httpd"].server_close()
            print("Server shut down successfully.")
            # Adding a delay to ensure port release
            time.sleep(1)
