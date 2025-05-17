from smtplib import SMTP
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def sendmail(email, url):
    from_addr = '11336017@ntub.edu.tw'
    to_addr = email

    with open('templates/verify.html', 'r') as file:
        file_data = ''
        content = file.readlines()

        for line in content:
            if '<p></p>' in line:
                line = line.replace('<p></p>', f"<p><a href=\"https://kuohao.wtf/verify/{url}\">認證</a></p>")
            file_data += line

    # print(content)
    #
    # content = f"""
    # <html>
    # <body>
    # <p>請點選下方的連結進行驗證 ：</p>
    # <p><a href="{url}">認證</a></p>
    # </body>
    # </html>
    # """

    msg = MIMEMultipart()
    msg.attach(MIMEText(file_data, 'html', 'utf-8'))

    msg['Subject'] = 'DataTrade - 請點選連結驗證您的信箱'
    msg['From'] = 'DataTrade <10856033@gmail.com>'
    msg['To'] = email

    smtp = SMTP('smtp.gmail.com', 587)
    smtp.ehlo()
    smtp.starttls()
    smtp.login('10856033@ntub.edu.tw', 'gxyouohswmsmhwzk')

    smtp.sendmail(from_addr, to_addr, msg.as_string())
