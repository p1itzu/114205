from smtplib import SMTP
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

from config import settings

def sendmail(email, verification_url):
    baseurl = settings.BASE_URL
    from_addr = '11336017@ntub.edu.tw'
    to_addr = email

    # 修正模板路徑
    template_path = os.path.join('templates', 'verify.html')
    
    try:
        with open(template_path, 'r', encoding='utf-8') as file:
            file_data = file.read()
            
        # 完整的驗證連結
        full_verification_url = f"{baseurl}/{verification_url}"
        
        # 替換驗證連結和按鈕
        if '<p></p>' in file_data:
            # 替換空的 <p></p> 為驗證按鈕
            verify_button = f'<a href="{full_verification_url}" class="verify-button">立即驗證信箱</a>'
            file_data = file_data.replace('<p></p>', verify_button)
            
        # 替換備用連結
        if '[驗證連結將在此處顯示]' in file_data:
            file_data = file_data.replace('[驗證連結將在此處顯示]', full_verification_url)

        msg = MIMEMultipart()
        msg.attach(MIMEText(file_data, 'html', 'utf-8'))

        msg['Subject'] = '味你而煮 - 請驗證您的信箱'
        msg['From'] = '味你而煮 <11336017@ntub.edu.tw>'
        msg['To'] = email

        smtp = SMTP('smtp.gmail.com', 587)
        smtp.ehlo()
        smtp.starttls()
        smtp.login('11336017@ntub.edu.tw', 'pzap ncvo mkfz xkaj')

        smtp.sendmail(from_addr, to_addr, msg.as_string())
        smtp.quit()
        
        return True
        
    except Exception as e:
        print(f"發送郵件失敗: {e}")
        return False
