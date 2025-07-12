from flask import Flask, render_template, request, session, redirect, url_for
from scipy.stats import norm
import io
import base64
import matplotlib
matplotlib.use('Agg')  # 이 줄을 추가!
import matplotlib.pyplot as plt


app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # 세션 사용을 위한 시크릿키

def calculate_asb_yield(mean, sigma, kpi_criteria):
    # X/10보다 큰 확률: 1 - CDF(X/10)
    threshold = kpi_criteria / 10
    prob = 1 - norm.cdf(threshold, loc=mean, scale=sigma)
    return round(prob, 6)

def calculate_price(kpi_value, price_max, price_min):
    # kpi_value: KPI 기준/10 값, price_max: 판가 상한, price_min: 판가 하한
    if kpi_value >= 100:
        return price_max
    elif kpi_value <= 80:
        return price_min
    else:
        # 선형 보간: price = price_min + (kpi_value - 80) * (price_max-price_min)/(100-80)
        return round(price_min + (kpi_value - 80) * (price_max - price_min) / 20, 2)

@app.route('/', methods=['GET', 'POST'])
def index():
    asb_yield = None
    price = None
    plot_url = None
    # AC 성능, 표준편차, 판가 상한/하한을 세션에 저장
    if 'ac_performance' not in session:
        session['ac_performance'] = ''
    if 'std_dev' not in session:
        session['std_dev'] = ''
    if 'price_max' not in session:
        session['price_max'] = '220'
    if 'price_min' not in session:
        session['price_min'] = '190'
    if 'log' not in session:
        session['log'] = []
    if request.method == 'POST':
        try:
            if request.form['ac_performance']:
                session['ac_performance'] = request.form['ac_performance']
            if request.form['std_dev']:
                session['std_dev'] = request.form['std_dev']
            if request.form['price_max']:
                session['price_max'] = request.form['price_max']
            if request.form['price_min']:
                session['price_min'] = request.form['price_min']
            mean = float(session['ac_performance'])
            sigma = float(session['std_dev'])
            price_max = float(session['price_max'])
            price_min = float(session['price_min'])
            kpi_criteria = float(request.form['kpi_criteria'])
            asb_yield = calculate_asb_yield(mean, sigma, kpi_criteria)
            kpi_value = kpi_criteria / 10
            price = calculate_price(kpi_value, price_max, price_min)
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
        # KPI 기준 오름차순으로 정렬
        sorted_logs = sorted(logs, key=lambda entry: entry['kpi_criteria'])
        x = [entry['kpi_criteria'] for entry in sorted_logs]
        y = [entry['asb_yield'] for entry in sorted_logs]
        price_y = [entry['price'] for entry in sorted_logs]
        import matplotlib
        matplotlib.use('Agg')  # 서버 환경에서 백엔드 설정
        matplotlib.rcParams['font.family'] = ['Malgun Gothic', 'AppleGothic', 'NanumGothic', 'DejaVu Sans', 'Arial', 'sans-serif']
        matplotlib.rcParams['axes.unicode_minus'] = False
        fig, ax1 = plt.subplots(figsize=(4,3))
        color1 = '#2a4d8f'
        color2 = 'red'
        ax1.plot(x, y, marker='o', color=color1, label='ASB 수율')
        ax1.set_xlabel('KPI 기준')
        ax1.set_ylabel('ASB 수율', color=color1)
        ax1.tick_params(axis='y', labelcolor=color1)
        ax1.set_title('KPI 기준 vs ASB 수율/판가')
        ax1.grid(True, linestyle='--', alpha=0.3)
        ax2 = ax1.twinx()
        ax2.plot(x, price_y, marker='s', color=color2, label='판가')
        ax2.set_ylabel('판가($)', color=color2)
        ax2.tick_params(axis='y', labelcolor=color2)
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plot_url = base64.b64encode(buf.getvalue()).decode('utf8')
        plt.close()
    return render_template('index.html', asb_yield=asb_yield, price=price, logs=logs,
                           ac_performance=session.get('ac_performance', ''),
                           std_dev=session.get('std_dev', ''),
                           price_max=session.get('price_max', '220'),
                           price_min=session.get('price_min', '190'),
                           plot_url=plot_url)

@app.route('/reset', methods=['POST'])
def reset():
    session.pop('ac_performance', None)
    session.pop('std_dev', None)
    session['log'] = []
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
