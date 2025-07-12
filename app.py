from flask import Flask, render_template, request, session, redirect, url_for
from scipy.stats import norm
import io
import base64
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # 세션 사용을 위한 시크릿키

def calculate_asb_yield(mean, sigma, kpi_criteria):
    # X/10보다 큰 확률: 1 - CDF(X/10)
    threshold = kpi_criteria / 10
    prob = 1 - norm.cdf(threshold, loc=mean, scale=sigma)
    return round(prob, 6)

def calculate_price(kpi_value):
    # kpi_value: KPI 기준/10 값
    if kpi_value >= 100:
        return 220
    elif kpi_value <= 80:
        return 190
    else:
        # 선형 보간: price = 190 + (kpi_value - 80) * 1.5
        return round(190 + (kpi_value - 80) * 1.5, 2)

@app.route('/', methods=['GET', 'POST'])
def index():
    asb_yield = None
    price = None
    plot_url = None
    # AC 성능, 표준편차를 세션에 저장
    if 'ac_performance' not in session:
        session['ac_performance'] = ''
    if 'std_dev' not in session:
        session['std_dev'] = ''
    if 'log' not in session:
        session['log'] = []
    if request.method == 'POST':
        try:
            # 입력값이 비어있지 않으면 세션에 저장
            if request.form['ac_performance']:
                session['ac_performance'] = request.form['ac_performance']
            if request.form['std_dev']:
                session['std_dev'] = request.form['std_dev']
            mean = float(session['ac_performance'])
            sigma = float(session['std_dev'])
            kpi_criteria = float(request.form['kpi_criteria'])
            asb_yield = calculate_asb_yield(mean, sigma, kpi_criteria)
            kpi_value = kpi_criteria / 10
            price = calculate_price(kpi_value)
            # 로그 저장
            log_entry = {
                'kpi_criteria': kpi_criteria,
                'asb_yield': asb_yield,
                'price': price
            }
            logs = session.get('log', [])
            logs.append(log_entry)
            session['log'] = logs
        except Exception:
            asb_yield = '입력 오류'
            price = '입력 오류'
    logs = session.get('log', [])
    # 그래프 생성: X=KPI 기준, Y=ASB 수율
    if logs:
        x = [entry['kpi_criteria'] for entry in logs]
        y = [entry['asb_yield'] for entry in logs]
        plt.figure(figsize=(4,3))
        plt.plot(x, y, marker='o', color='#2a4d8f')
        plt.xlabel('KPI 기준')
        plt.ylabel('ASB 수율')
        plt.title('KPI 기준 vs ASB 수율')
        plt.grid(True, linestyle='--', alpha=0.3)
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plot_url = base64.b64encode(buf.getvalue()).decode('utf8')
        plt.close()
    return render_template('index.html', asb_yield=asb_yield, price=price, logs=logs,
                           ac_performance=session.get('ac_performance', ''),
                           std_dev=session.get('std_dev', ''),
                           plot_url=plot_url)

@app.route('/reset', methods=['POST'])
def reset():
    session.pop('ac_performance', None)
    session.pop('std_dev', None)
    session['log'] = []
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
