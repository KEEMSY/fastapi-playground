import pandas as pd
import sys
import os

def analyze(results_dir):
    def get_stats(file_prefix):
        file_path = f"{file_prefix}_stats.csv"
        if not os.path.exists(file_path):
            return None
        df = pd.read_csv(file_path)
        # Aggregated 행 추출
        agg = df[df['Name'] == 'Aggregated'].iloc[0]
        return {
            'Requests': int(agg['Request Count']),
            'Failures': int(agg['Failure Count']),
            'RPS': round(float(agg['Requests Per Second']), 2),
            'Avg Resp (ms)': int(agg['Average Response Time']),
            'Max Resp (ms)': int(agg['Max Response Time']),
            'Success Rate (%)': round((1 - float(agg['Failure Count'])/float(agg['Request Count'])) * 100, 2) if agg['Request Count'] > 0 else 0
        }

    case1 = get_stats(os.path.join(results_dir, "case1_vertical"))
    case2 = get_stats(os.path.join(results_dir, "case2_horizontal"))

    if case1 is None or case2 is None:
        print("Error: Could not find result CSV files.")
        return

    report = pd.DataFrame([case1, case2], index=['Vertical (1 Inst, Pool 60)', 'Horizontal (3 Inst, Pool 20)'])
    
    print("\n" + "="*90)
    print(" 전략 비교 테스트 결과 리포트 (Strategy Comparison Report)")
    print("="*90)
    print(report.to_string())
    print("="*90)
    
    # 분석 코멘트
    print("\n[분석 결과]")
    if case2['Success Rate (%)'] > case1['Success Rate (%)']:
        print("- 수평 확장(Horizontal)이 더 높은 성공률을 보여줍니다.")
    elif case2['Success Rate (%)'] < case1['Success Rate (%)']:
        print("- 수직 확장(Vertical)이 더 높은 성공률을 보여줍니다.")
    else:
        print("- 두 전략의 성공률이 동일합니다.")

    if case2['Avg Resp (ms)'] < case1['Avg Resp (ms)']:
        print(f"- 수평 확장(Horizontal)이 평균 응답 속도 면에서 {case1['Avg Resp (ms)'] - case2['Avg Resp (ms)']}ms 더 빠릅니다.")
    elif case2['Avg Resp (ms)'] > case1['Avg Resp (ms)']:
        print(f"- 수직 확장(Vertical)이 평균 응답 속도 면에서 {case2['Avg Resp (ms)'] - case1['Avg Resp (ms)']}ms 더 빠릅니다.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_comparison.py <results_directory>")
    else:
        analyze(sys.argv[1])
