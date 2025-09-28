import os
import sys
import smtplib
import io
import base64
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
plt.rcParams["font.family"] = ["SimHei"]
plt.rcParams['axes.unicode_minus'] = False
# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from taobao_price_monitor.config.config import EMAIL_CONFIG

class EmailSender:
    def __init__(self):
        self.smtp_server = EMAIL_CONFIG['smtp_server']
        self.smtp_port = EMAIL_CONFIG['smtp_port']
        self.sender = EMAIL_CONFIG['sender']
        self.password = EMAIL_CONFIG['password']  # SMTP授权码

    def send_price_alert(self, receiver, info):
        """发送价格变动提醒邮件"""
        msg = MIMEMultipart()
        msg['From'] = self.sender
        msg['To'] = receiver
        msg['Subject'] = f"价格提醒：{info['name']}"
        
        img_data = self._generate_price_chart(info)

        image = MIMEImage(img_data.getvalue(), name='price_chart.png')
        image.add_header('Content-ID', '<price_chart>')
        msg.attach(image)
        
        # HTML内容
        change_type = '上涨' if info['price_change'] > 0 else '下跌'
        change_text = f"{abs(info['price_change']):+.2f}%" if info['price_change'] != 0 else "持平"
        
        html = f"""
        <html>
            <body>
                <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
                    <h2 style="color: #333; border-bottom: 2px solid #f0f0f0; padding-bottom: 10px;">{info['name']}</h2>
                    
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                        <tr>
                            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">当前价格:</td>
                            <td style="padding: 10px; border: 1px solid #ddd;">{info['price']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">价格变化:</td>
                            <td style="padding: 10px; border: 1px solid #ddd; color: {'red' if info['price_change'] > 0 else 'green'};">{change_type} {change_text}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">历史最高价:</td>
                            <td style="padding: 10px; border: 1px solid #ddd;">{info['his_high_price']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">历史最低价:</td>
                            <td style="padding: 10px; border: 1px solid #ddd;">{info['his_low_price']}</td>
                        </tr>
                    </table>
                    
                    <div style="margin: 20px 0;">
                        <h3 style="color: #555;">价格趋势图</h3>
                        <img src="cid:price_chart" style="max-width: 100%; height: auto;" />
                    </div>
                    
                    <div style="margin-top: 20px;">
                        <a href="{info['link']}" style="display: inline-block; padding: 10px 20px; background-color: #1677ff; color: white; text-decoration: none; border-radius: 4px;">查看商品详情</a>
                    </div>
                </div>
            </body>
        </html>
        """
        msg.attach(MIMEText(html, 'html', 'utf-8'))
        
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # 启用TLS加密
                server.login(self.sender, self.password)
                server.send_message(msg)
            print(f"邮件已发送至 {receiver}")
        except smtplib.SMTPResponseException as e:
            # 忽略特定的SMTP响应异常，继续执行
            print(f"邮件发送至 {receiver} 完成，但服务器关闭连接时有响应异常: {e}")
        except Exception as e:
            # 捕获其他可能的异常
            print(f"发送邮件至 {receiver} 时出错: {e}")

    def _generate_price_chart(self, info):
        """生成价格趋势图"""
        # 准备数据
        dates = []
        prices = []
        x_labels = []  # 用于存储自定义x轴标签
        
        for date_str, price in info['priceList']:
            date = datetime.strptime(date_str, '%Y/%m/%d')
            dates.append(date)
            prices.append(price)
            x_labels.append(date_str)

        current_price = info['price']
        if dates:
            now_date = dates[-1] + timedelta(days=1)
        else:
            now_date = datetime.now()
        dates.append(now_date)
        prices.append(current_price)
        x_labels.append('now')
        
        # 创建图表
        plt.figure(figsize=(10, 6))

        if len(dates) > 1:
            plt.plot(dates[:-1], prices[:-1], marker='o', linestyle='-', color='#1677ff', label='价格趋势')
        high_price = info['his_high_price']
        low_price = info['his_low_price']
        
        # 添加最高价水平虚线
        plt.axhline(y=high_price, color='red', linestyle='--', linewidth=1, label=f'历史最高价: {high_price}')
        
        # 添加最低价水平虚线
        plt.axhline(y=low_price, color='green', linestyle='--', linewidth=1, label=f'历史最低价: {low_price}')
        plt.scatter(dates[-1], prices[-1], color='orange', s=200, zorder=10, edgecolors='black', linewidths=2, label=f'当前价格: {current_price}')
        plt.annotate(f'当前价格: {current_price}',
                     xy=(dates[-1], prices[-1]),
                     xytext=(10, 10),
                     textcoords='offset points',
                     ha='left',
                     color='orange',
                     fontsize=10,
                     fontweight='bold',
                     arrowprops=dict(arrowstyle='->', color='orange'))
        
        plt.title(f'{info["name"]} 价格趋势', fontsize=14)
        plt.xlabel('日期', fontsize=12)
        plt.ylabel('价格', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        
        plt.xticks(dates, x_labels, rotation=45)
        
        plt.tight_layout()
        plt.legend()
        
        # 将图表保存到内存
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        
        return buf

# 测试，调用示例：
# 备注：哥们你调用的时候记得在外面先算出来需要的info，比如priceList，his_high_price，his_low_price等，
# 然后实例化EmailSender类，调用send_price_alert方法传参即可
# config里我配置了EMAIL_CONFIG，这是我自己的QQ邮箱的stmp配置，别乱传，你后续可以换成自己的，认证码（password）怎么搞你自己找一下ai问一问

if __name__ == "__main__":
    # 准备测试数据
    test_info = {
        'name': '测试商品',
        'price': 97,
        'price_change': -16.67,
        'priceList': [
            ('2024/06/01', 120.00),
            ('2024/06/05', 125.00),
            ('2024/06/10', 115.00),
            ('2024/06/15', 110.00),
            ('2024/06/20', 100.00),
            ('2024/06/25', 105.00),
            ('2024/06/30', 100.00)
        ],
        'link': 'https://example.com',
        'his_high_price': 125.00,
        'his_low_price': 100.00
    }
    sender = EmailSender()
    # 使用配置中的接收者列表
    for receiver in EMAIL_CONFIG['receivers']:
        sender.send_price_alert(receiver, test_info)
