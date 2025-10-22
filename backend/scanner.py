import json

def analyze_properties():
    with open('mock_data.json', 'r', encoding='utf-8') as f:
        properties = json.load(f)

    print("\n--- 모의 데이터 분석 시작 ---\n")

    # 불러온 모든 매물에 대해 반복 분석
    for prop in properties:
        warnings = []
        checklist = []

        # --- 1. 위험 분석 로직 ---
        # 분석 1: 전세가율 계산
        sale_price = int(prop['매매가'])
        jeonse_price = int(prop['전세가'])
        jeonse_rate = (jeonse_price / sale_price) * 100
        
        if jeonse_rate >= 80:
            warnings.append(f"🚨 위험: 전세가율이 {jeonse_rate:.1f}%로 매우 높습니다.")
            checklist.append("HUG 보증보험 가입이 거절될 수 있으니 최우선으로 확인하세요.")
        elif jeonse_rate >= 70:
            warnings.append(f"⚠️ 주의: 전세가율이 {jeonse_rate:.1f}%로 높은 편입니다.")
            checklist.append("HUG 보증보험 가입 가능 여부를 반드시 확인하고 특약에 명시하세요.")
        else:
            warnings.append(f"✅ 양호: 전세가율이 {jeonse_rate:.1f}%로 안정적입니다.")

        # 분석 2: 악성 임대인 여부
        if prop['집주인_악성임대인여부']:
            warnings.append("🔥🔥🔥 치명적 위험: 임대인이 악성 임대인 명단에 포함되어 있습니다!")
            checklist.append("절대로 계약해서는 안 되는 매물입니다. 즉시 거래를 중단하세요.")

        # --- 2. 기본 체크리스트 추가 ---
        checklist.append("계약 직전 등기부등본을 다시 발급받아 변동사항이 없는지 최종 확인하세요.")
        checklist.append("임대인 신분증과 등기부등본 상 소유주가 일치하는지 대조하세요.")

        # --- 3. 최종 결과 출력 ---
        print(f"--- {prop['아파트']} 분석 결과 ---")
        for warning in warnings:
            print(warning)
        
        print("\n[맞춤형 체크리스트]")
        for i, item in enumerate(checklist, 1):
            print(f"{i}. {item}")
        print("-" * 30 + "\n")

# 메인 함수 실행
analyze_properties()