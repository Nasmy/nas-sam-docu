import re
import json

def extract_info(text):
    # Define regex patterns
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    social_media_pattern = r'@[a-zA-Z0-9_]+'
    hashtag_pattern = r'#\w+'
    file_path_pattern = r'[a-zA-Z]:\\(?:[^<>:"/\\|?*\n\r]+\\)*[^<>:"/\\|?*\n\r]*'
    percentage_pattern = r'\b\d+(\.\d+)?%\b'

    # Extract information
    emails = re.findall(email_pattern, text)
    urls = re.findall(url_pattern, text)
    social_media_handles = re.findall(social_media_pattern, text)
    hashtags = re.findall(hashtag_pattern, text)
    file_paths = re.findall(file_path_pattern, text)
    percentages = re.findall(percentage_pattern, text)

    # Create JSON output
    output = {
        'Emails': emails,
        'URLs': urls,
        'Social Media Handles': social_media_handles,
        'Hashtags': hashtags,
        'File Paths': file_paths,
        'Percentages': percentages,
    }

    return json.dumps(output, indent=4)