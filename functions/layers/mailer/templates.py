class EmailVerificationTemplate:
    SUBJECT = "Verify your email on DocuDiveAI"

    VERIFICATION_EMAIL_PLAINTEXT = """
        Thanks for registering with docudiveai.com.
        To verify your email, please copy the following link and paste in a new browser tab.
        {0}
        """

    VERIFICATION_EMAIL_HTML = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Verify Your Email</title>
        <style>
            /* Add any custom styles you want here */
            body {{
                font-family: Arial, sans-serif;
            }}
            .container {{
                max-width: 600px;
                margin: 20px auto;
                padding: 20px;
                border: 1px solid #e0e0e0;
                border-radius: 10px;
            }}
            .btn {{
                display: inline-block;
                padding: 10px 20px;
                margin-top: 20px;
                color: white;
                background-color: #007BFF;
                border-radius: 5px;
                text-decoration: none;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <p>Thanks for registering with <a href="https://docudiveai.com" target="_blank">docudiveai.com</a>.</p>
            <p>To verify your email, please click the button below:</p>
            <a href="{0}" class="btn" target="_blank">Verify Email</a>
            <p style="margin-top:20px;">Or, if you prefer, you can copy and paste the following link into your browser:</p>
            <p><a href="{0}" target="_blank">{0}</a></p>
        </div>
    </body>
    </html>
    """


class EmailResetTemplate:
    SUBJECT = "Reset your password on DocuDiveAI"

    VERIFICATION_EMAIL_PLAINTEXT = """
        To reset your password, please copy the following link and paste in a new browser tab.
        {0}
        """

    VERIFICATION_EMAIL_HTML = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Reset Your Password</title>
        <style>
            /* Add any custom styles you want here */
            body {{
                font-family: Arial, sans-serif;
            }}
            .container {{
                max-width: 600px;
                margin: 20px auto;
                padding: 20px;
                border: 1px solid #e0e0e0;
                border-radius: 10px;
            }}
            .btn {{
                display: inline-block;
                padding: 10px 20px;
                margin-top: 20px;
                color: white;
                background-color: #007BFF;
                border-radius: 5px;
                text-decoration: none;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <p>To reset your password, please click the button below:</p>
            <a href="{0}" class="btn" target="_blank">Reset Password</a>
            <p style="margin-top:20px;">Or, if you prefer, you can copy and paste the following link into your browser:</p>
            <p><a href="{0}" target="_blank">{0}</a></p>
        </div>
    </body>
    </html>
    """