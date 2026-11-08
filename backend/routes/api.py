"""API 라우트 핸들러"""
import re
from flask import jsonify, request
from flask_login import login_required, current_user
from datetime import datetime, timezone, timedelta
from utils import (
    TransactionSourceError, _resolve_lawd_cd, load_transaction_snapshot,
    filter_transactions_by_region, get_heatmap_data, _save_heatmap_to_db,
    fetch_properties_by_region, analyze_property_warnings, generate_safety_checklist,
)
from models import SearchHistory, Favorite, Review, Report, Notification, RealTransaction, HeatmapData
from time_utils import format_kst_datetime, get_kst_now

def _parse_deal_date(deal_date_str):
    try:
        date_str = deal_date_str.replace('-', '') if '-' in deal_date_str else deal_date_str
        if len(date_str) >= 8:
            return datetime(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))
    except (ValueError, TypeError):
        pass
    return None

def generate_real_notifications(db, HeatmapData, RealTransaction):
    notifications = []
    now = get_kst_now().replace(tzinfo=None)
    one_day_ago = now - timedelta(days=1)
    try:
        high_risk_regions = HeatmapData.query.filter(HeatmapData.score >= 80).order_by(HeatmapData.score.desc()).limit(3).all()
        if high_risk_regions:
            for region_data in high_risk_regions:
                notifications.append({
                    'title': '🚨 위험지역 경고',
                    'message': f'{region_data.region}의 전세사기 위험도가 {region_data.score}점으로 높습니다. 계약 시 주의하세요.',
                    'type': 'danger',
                    'user_id': None
                })
    except Exception:
        pass
    try:
        recent_properties = RealTransaction.query.filter(RealTransaction.created_at >= one_day_ago).order_by(RealTransaction.created_at.desc()).limit(5).all()
        if recent_properties:
            regions = {}
            for prop in recent_properties:
                region = prop.region or prop.dong_name or '알 수 없음'
                if region not in regions:
                    regions[region] = []
                regions[region].append(prop)
            for region, props in list(regions.items())[:3]:
                notifications.append({
                    'title': '🏠 새로운 매물 등록',
                    'message': f'{region}에 새로운 매물 {len(props)}건이 등록되었습니다.',
                    'type': 'info',
                    'user_id': None
                })
    except Exception:
        pass
    try:
        thirty_days_ago = now - timedelta(days=30)
        all_deals = RealTransaction.query.filter(RealTransaction.deal_date.isnot(None), RealTransaction.deal_date != '').all()
        recent_deals = []
        for deal in all_deals:
            deal_datetime = _parse_deal_date(deal.deal_date)
            if deal_datetime and deal_datetime >= thirty_days_ago:
                recent_deals.append(deal)
            elif deal.created_at and deal.created_at >= (now - timedelta(days=7)):
                recent_deals.append(deal)
        def get_deal_datetime(deal):
            deal_dt = _parse_deal_date(deal.deal_date) if deal.deal_date else None
            return deal_dt or deal.created_at or datetime(2000, 1, 1)
        recent_deals.sort(key=get_deal_datetime, reverse=True)
        recent_deals = recent_deals[:10]
        if recent_deals:
            deal_regions = {}
            for deal in recent_deals:
                region = deal.region or deal.dong_name or '알 수 없음'
                if region not in deal_regions:
                    deal_regions[region] = []
                deal_regions[region].append(deal)
            for region, deals in list(deal_regions.items())[:3]:
                count = len(deals)
                prices = [d.price for d in deals if d.price and d.price > 0]
                if prices:
                    avg_price = sum(prices) / len(prices)
                    from utils import _format_price_to_eok
                    price_str = _format_price_to_eok(int(avg_price))
                    print(f"[알림] {region} 평균 가격: {avg_price}만원 -> {price_str}")
                else:
                    price_str = '가격 정보 없음'
                notifications.append({
                    'title': '💰 최근 거래 매물',
                    'message': f'{region}에서 최근 거래 {count}건이 발생했습니다. 평균 가격: {price_str}',
                    'type': 'success',
                    'user_id': None
                })
    except Exception as e:
        pass
    return notifications

def register_api_routes(app, db):
    from models import RealTransaction, HeatmapData
    @app.route('/heatmap')
    def heatmap():
        data = get_heatmap_data(db, HeatmapData, RealTransaction, force_update=False)
        return jsonify(data)
    @app.route('/api/heatmap/refresh', methods=['POST'])
    def refresh_heatmap():
        try:
            data = get_heatmap_data(db, HeatmapData, RealTransaction, force_update=True)
            return jsonify({'success': True, 'data': data, 'message': f'{len(data)}개 지역 데이터가 최신 전세가율로 업데이트되었습니다.'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    @app.route('/api/heatmap/update', methods=['POST'])
    def update_heatmap():
        try:
            data = request.get_json()
            if not data or not isinstance(data, list):
                return jsonify({'error': 'Invalid data format'}), 400
            updated_data = []
            for region_info in data:
                region = region_info.get('region')
                if not region:
                    continue
                properties = fetch_properties_by_region(region, db, RealTransaction)
                properties_with_rate = [p for p in properties if p.get('jeonse_rate') is not None and p.get('jeonse_rate') > 0]
                if properties_with_rate:
                    avg_rate = sum(p['jeonse_rate'] for p in properties_with_rate) / len(properties_with_rate)
                    score = round(avg_rate)
                else:
                    continue
                updated_data.append({
                    'region': region,
                    'score': score,
                    'lat': region_info.get('lat', 0),
                    'lng': region_info.get('lng', 0)
                })
            _save_heatmap_to_db(db, HeatmapData, updated_data)
            return jsonify({'success': True, 'message': f'{len(updated_data)}개 지역 데이터가 전세가율 기반으로 업데이트되었습니다.'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    def property_payload(prop):
        fields = ('name', 'price', 'price_raw', 'address', 'area', 'floor', 'build_year',
                  'deal_date', 'jeonse_rate', 'risk_level', 'risk_score',
                  'comparison_sample_count', 'comparison_status', 'comparison_confidence')
        return dict({field: prop.get(field) for field in fields},
                    jeonse_price=prop.get('jeonse_price_formatted') or '-',
                    jeonse_price_raw=prop.get('jeonse_price'),
                    warnings=analyze_property_warnings(prop),
                    checklist=generate_safety_checklist(prop))

    @app.route('/api/analyze')
    @app.route('/analyze')
    def analyze():
        region = request.args.get('region', '').strip()
        if not region:
            return jsonify(error='지역명을 입력하세요'), 400
        try:
            properties = fetch_properties_by_region(region, db, RealTransaction)
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        except TransactionSourceError:
            return jsonify(error='매매 실거래 자료를 불러오지 못했습니다. 잠시 후 다시 시도하세요.'), 502
        return jsonify(properties=[property_payload(prop) for prop in properties])

    @app.route('/api/real-transactions')
    def api_real_transactions():
        region = request.args.get('region', '').strip()
        lawd_cd = request.args.get('lawd_cd') or _resolve_lawd_cd(region, fallback=None)
        deal_ymd = request.args.get('deal_ymd') or datetime.now(timezone(timedelta(hours=9))).strftime('%Y%m')
        try:
            page_no = int(request.args.get('pageNo', 1))
            rows = int(request.args.get('numOfRows', 30))
            if not lawd_cd or not re.fullmatch(r'[0-9]{5}', lawd_cd):
                raise ValueError()
            if not re.fullmatch(r'[0-9]{6}', deal_ymd):
                raise ValueError()
            datetime.strptime(deal_ymd + '01', '%Y%m%d')
            if not 1 <= page_no <= 20000 or not 1 <= rows <= 100:
                raise ValueError()
        except ValueError:
            return jsonify(error='지역코드, 거래월 또는 페이지 요청이 올바르지 않습니다.'), 400
        try:
            transactions = filter_transactions_by_region(load_transaction_snapshot('sale', lawd_cd, deal_ymd), region)
        except TransactionSourceError:
            return jsonify(error='매매 실거래 자료를 불러오지 못했습니다. 잠시 후 다시 시도하세요.'), 502
        offset = (page_no - 1) * rows
        return jsonify(transactions=transactions[offset:offset + rows], total_count=len(transactions),
                       page_no=page_no, page_size=rows, has_more=offset + rows < len(transactions))

    @app.route('/api/advanced-search')
    def advanced_search():
        region = request.args.get('region', '')
        min_price = request.args.get('min_price', type=int)
        max_price = request.args.get('max_price', type=int)
        property_type = request.args.get('property_type', '')
        risk_level = request.args.get('risk_level', '')
        try:
            properties = fetch_properties_by_region(region.strip(), db, RealTransaction)
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        except TransactionSourceError:
            return jsonify(error='매매 실거래 자료를 불러오지 못했습니다. 잠시 후 다시 시도하세요.'), 502
        filtered_properties = []
        for prop in properties:
            if min_price or max_price:
                try:
                    price_raw = prop.get('price_raw', 0)
                    if price_raw:
                        prop_price_eok = price_raw / 10000
                        if min_price and prop_price_eok < min_price:
                            continue
                        if max_price and prop_price_eok > max_price:
                            continue
                except (ValueError, TypeError):
                    pass
            if property_type and property_type not in prop.get('name', ''):
                continue
            if risk_level and prop.get('risk_level') != risk_level:
                continue
            filtered_properties.append(property_payload(prop))
        return jsonify({'properties': filtered_properties})
    @app.route('/api/search-history', methods=['GET', 'POST'])
    def search_history():
        if request.method == 'POST':
            if current_user.is_authenticated:
                data = request.get_json()
                region_raw = data['region']
                region_dong = _extract_dong(region_raw)
                jeonse_rate = None
                try:
                    heatmap_data = HeatmapData.query.filter_by(region=region_dong).first()
                    if heatmap_data:
                        jeonse_rate = float(heatmap_data.score)
                    else:
                        from utils import _calculate_jeonse_rate_score
                        properties = fetch_properties_by_region(region_dong, db, RealTransaction)
                        if properties:
                            jeonse_rate = _calculate_jeonse_rate_score(properties)
                except Exception as e:
                    print(f"[검색 히스토리] 전세가율 계산 실패: {str(e)}")
                history = SearchHistory(user_id=current_user.id, region=region_dong, risk_score=int(round(jeonse_rate)) if jeonse_rate is not None else None)
                db.session.add(history)
                db.session.commit()
            return jsonify({'status': 'success'})
        else:
            if current_user.is_authenticated:
                histories = SearchHistory.query.filter_by(user_id=current_user.id).order_by(SearchHistory.search_date.desc()).limit(10).all()
                result = []
                seen_regions = set()
                for h in histories:
                    if h.region in seen_regions:
                        continue
                    seen_regions.add(h.region)
                    jeonse_rate = None
                    try:
                        heatmap_data = HeatmapData.query.filter_by(region=h.region).first()
                        if heatmap_data:
                            jeonse_rate = float(heatmap_data.score)
                        elif h.risk_score is not None:
                            jeonse_rate = float(h.risk_score)
                    except Exception:
                        if h.risk_score is not None:
                            jeonse_rate = float(h.risk_score)
                    result.append({
                        'id': h.id,
                        'region': h.region,
                        'search_date': format_kst_datetime(h.search_date, '%Y-%m-%d %H:%M:%S'),
                        'risk_score': round(jeonse_rate, 1) if jeonse_rate is not None else None,
                        'jeonse_rate': round(jeonse_rate, 1) if jeonse_rate is not None else None
                    })
                return jsonify(result)
            return jsonify([])
    @app.route('/api/search-history/<int:history_id>', methods=['DELETE'])
    @login_required
    def delete_search_history(history_id):
        history = SearchHistory.query.get_or_404(history_id)
        if history.user_id != current_user.id:
            return jsonify({'error': '권한이 없습니다'}), 403
        db.session.delete(history)
        db.session.commit()
        return jsonify({'status': 'success'})
    @app.route('/api/search-history/all', methods=['DELETE'])
    @login_required
    def delete_all_search_history():
        deleted_count = SearchHistory.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        return jsonify({'status': 'success', 'deleted_count': deleted_count})
    @app.route('/api/favorites', methods=['GET', 'POST', 'DELETE'])
    def favorites():
        if request.method == 'POST':
            if not current_user.is_authenticated:
                return jsonify({'status': 'error', 'message': '로그인이 필요합니다'}), 401
            data = request.get_json()
            existing = Favorite.query.filter_by(user_id=current_user.id, region=data['region']).first()
            if existing:
                return jsonify({'status': 'success', 'message': '이미 즐겨찾기에 추가된 지역입니다'})
            favorite = Favorite(user_id=current_user.id, region=data['region'], created_at=get_kst_now().replace(tzinfo=None))
            db.session.add(favorite)
            db.session.commit()
            return jsonify({'status': 'success'})
        elif request.method == 'DELETE':
            if not current_user.is_authenticated:
                return jsonify({'status': 'error', 'message': '로그인이 필요합니다'}), 401
            data = request.get_json()
            Favorite.query.filter_by(user_id=current_user.id, region=data['region']).delete()
            db.session.commit()
            return jsonify({'status': 'success'})
        else:
            if current_user.is_authenticated:
                favorites = Favorite.query.filter_by(user_id=current_user.id).all()
                return jsonify([{'id': f.id, 'region': f.region, 'created_at': format_kst_datetime(f.created_at, '%Y-%m-%d %H:%M:%S')} for f in favorites])
            return jsonify([])
    @app.route('/api/favorites/<int:fav_id>', methods=['DELETE'])
    @login_required
    def delete_favorite(fav_id):
        favorite = Favorite.query.filter_by(id=fav_id, user_id=current_user.id).first()
        if favorite:
            db.session.delete(favorite)
            db.session.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': '즐겨찾기를 찾을 수 없습니다'}), 404
    @app.route('/api/reviews', methods=['GET', 'POST'])
    def reviews():
        region = request.args.get('region')
        if request.method == 'POST':
            if current_user.is_authenticated:
                data = request.get_json()
                review = Review(user_id=current_user.id, region=data['region'], rating=data['rating'], content=data.get('content', ''))
                db.session.add(review)
                db.session.commit()
                return jsonify({'status': 'success'})
            return jsonify({'error': '로그인이 필요합니다'}), 401
        else:
            query = Review.query
            if region:
                query = query.filter_by(region=region)
            reviews = query.order_by(Review.created_at.desc()).all()
            return jsonify({
                'reviews': [{
                    'id': r.id,
                    'username': r.user.username,
                    'region': r.region,
                    'rating': r.rating,
                    'content': r.content,
                    'created_at': format_kst_datetime(r.created_at, '%Y-%m-%d %H:%M'),
                    'user_id': r.user_id
                } for r in reviews],
                'current_user_id': current_user.id if current_user.is_authenticated else None
            })
    @app.route('/api/reviews/<int:review_id>', methods=['PUT', 'DELETE'])
    @login_required
    def review_detail(review_id):
        review = Review.query.get_or_404(review_id)
        if review.user_id != current_user.id:
            return jsonify({'error': '권한이 없습니다'}), 403
        if request.method == 'PUT':
            data = request.get_json()
            if 'region' in data:
                review.region = data['region']
            if 'rating' in data:
                review.rating = data['rating']
            if 'content' in data:
                review.content = data['content']
            db.session.commit()
            return jsonify({'status': 'success', 'message': '리뷰가 수정되었습니다.'})
        else:
            db.session.delete(review)
            db.session.commit()
            return jsonify({'status': 'success'})
    @app.route('/api/reports', methods=['GET', 'POST'])
    @login_required
    def reports():
        if request.method == 'GET':
            # 현재 사용자의 신고 목록 반환
            user_reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.created_at.desc()).all()
            return jsonify([{
                'id': r.id,
                'region': r.region,
                'property_address': r.property_address or '주소 정보 없음',
                'report_type': r.report_type,
                'status': r.status,
                'created_at': format_kst_datetime(r.created_at),
                'description': r.description or ''
            } for r in user_reports])
        else:
            data = request.get_json()
            report = Report(
                user_id=current_user.id,
                region=data.get('region', '알 수 없음'),
                property_address=data.get('property_address', ''),
                report_type=data.get('report_type', 'other'),
                description=data.get('description', '')
            )
            db.session.add(report)
            db.session.commit()
            return jsonify({'status': 'success', 'report_id': report.id})
    @app.route('/api/admin/reports', methods=['GET'])
    @login_required
    def admin_list_reports():
        if not getattr(current_user, 'is_admin', False):
            return jsonify({'error': '관리자만 사용할 수 있습니다'}), 403
        report_type_map = {
            'suspicious': '의심스러운 매물',
            'scam': '전세사기 의심',
            'fake': '가짜 매물',
            'other': '기타'
        }
        all_reports = Report.query.order_by(Report.created_at.desc()).all()
        return jsonify([{
            'id': r.id,
            'username': r.user.username if r.user else '알 수 없음',
            'region': r.region,
            'property_address': r.property_address or '주소 정보 없음',
            'report_type': r.report_type,
            'report_type_kr': report_type_map.get(r.report_type, r.report_type),
            'status': r.status,
            'description': r.description or '',
            'created_at': format_kst_datetime(r.created_at)
        } for r in all_reports])
    @app.route('/api/admin/reports/<int:report_id>/status', methods=['PUT'])
    @login_required
    def admin_update_report_status(report_id):
        if not getattr(current_user, 'is_admin', False):
            return jsonify({'error': '관리자만 사용할 수 있습니다'}), 403
        data = request.get_json() or {}
        new_status = data.get('status')
        if new_status not in ('pending', 'investigating', 'resolved'):
            return jsonify({'error': '올바르지 않은 상태 값입니다'}), 400
        report = Report.query.get_or_404(report_id)
        report.status = new_status
        db.session.commit()
        return jsonify({'status': 'success'})
    @app.route('/api/notifications', methods=['GET', 'PUT'])
    def notifications():
        if request.method == 'PUT':
            if current_user.is_authenticated:
                data = request.get_json()
                notification = Notification.query.get(data['id'])
                if notification and notification.user_id in (current_user.id, None):
                    notification.is_read = True
                    db.session.commit()
            return jsonify({'status': 'success'})
        else:
            try:
                sample_patterns = ['🚨 위험지역 경고', '✅ 분석 완료', 'ℹ️ 새로운 기능 안내', '📊 월간 리포트', '⚠️ 주의 필요']
                deleted_count = Notification.query.filter(Notification.title.in_(sample_patterns), Notification.user_id.isnot(None)).delete(synchronize_session=False)
                if deleted_count > 0:
                    db.session.commit()
            except Exception:
                db.session.rollback()
            try:
                one_hour_ago = get_kst_now().replace(tzinfo=None) - timedelta(hours=1)
                recent_notifications = Notification.query.filter(Notification.created_at >= one_hour_ago, Notification.user_id.is_(None)).count()
                if recent_notifications == 0:
                    real_notifications = generate_real_notifications(db, HeatmapData, RealTransaction)
                    created_count = 0
                    one_day_ago = get_kst_now().replace(tzinfo=None) - timedelta(days=1)
                    for notif_data in real_notifications:
                        existing = Notification.query.filter(Notification.title == notif_data['title'], Notification.message == notif_data['message'], Notification.created_at >= one_day_ago).first()
                        if not existing:
                            notification = Notification(user_id=notif_data['user_id'], title=notif_data['title'], message=notif_data['message'], type=notif_data['type'], is_read=False)
                            db.session.add(notification)
                            created_count += 1
                    if created_count > 0:
                        db.session.commit()
            except Exception:
                db.session.rollback()
            query = Notification.query
            if current_user.is_authenticated:
                query = query.filter((Notification.user_id == current_user.id) | (Notification.user_id.is_(None)))
            else:
                query = query.filter(Notification.user_id.is_(None))
            notifications = query.order_by(Notification.created_at.desc()).limit(5).all()
            return jsonify([{'id': n.id, 'title': n.title, 'message': n.message, 'type': n.type, 'is_read': n.is_read, 'created_at': format_kst_datetime(n.created_at, '%Y-%m-%d %H:%M'), 'user_id': n.user_id, 'is_public': n.user_id is None} for n in notifications])
    @app.route('/api/notifications/read-all', methods=['POST'])
    @login_required
    def read_all_notifications():
        try:
            Notification.query.filter((Notification.user_id == current_user.id) | (Notification.user_id.is_(None)), Notification.is_read == False).update({Notification.is_read: True}, synchronize_session=False)
            db.session.commit()
            return jsonify({'status': 'success', 'message': '모든 알림이 읽음으로 표시되었습니다.'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': str(e)}), 500
    @app.route('/api/notifications/<int:notif_id>/read', methods=['POST'])
    @login_required
    def read_notification(notif_id):
        notification = Notification.query.filter_by(id=notif_id).first()
        if notification and (notification.user_id == current_user.id or notification.user_id is None):
            notification.is_read = True
            db.session.commit()
            return jsonify({'success': True})
    @app.route('/api/notifications/all', methods=['DELETE'])
    @login_required
    def delete_all_notifications():
        try:
            deleted_count = Notification.query.filter_by(user_id=current_user.id).delete(synchronize_session=False)
            db.session.commit()
            return jsonify({'status': 'success', 'deleted_count': deleted_count, 'message': f'{deleted_count}개의 알림이 삭제되었습니다.'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': str(e)}), 500
    @app.route('/api/stats')
    def stats():
        total_analyses = SearchHistory.query.count()
        total_reports = Report.query.count()
        high_risk_regions = HeatmapData.query.filter(HeatmapData.score >= 80).count()
        total_regions = HeatmapData.query.count()
        return jsonify({
            'total_analyses': total_analyses,
            'total_searches': total_analyses,
            'total_reports': total_reports,
            'high_risk_regions': high_risk_regions,
            'total_regions': total_regions
        })
    @app.route('/api/yearly-reports')
    def yearly_reports():
        from sqlalchemy import extract, func
        yearly_data = db.session.query(extract('year', Report.created_at).label('year'), func.count(Report.id).label('count')).filter(extract('year', Report.created_at).between(2020, 2025)).group_by(extract('year', Report.created_at)).all()
        yearly_stats = {year: 0 for year in range(2020, 2026)}
        for year, count in yearly_data:
            yearly_stats[int(year)] = count
        return jsonify([{'year': year, 'count': yearly_stats[year]} for year in range(2020, 2026)])
    
    @app.route('/api/admin/delete-region', methods=['POST'])
    @login_required
    def delete_region_data():
        """특정 지역의 모든 데이터 삭제 (관리자용)"""
        if not current_user.is_admin:
            return jsonify(error="관리자만 사용할 수 있습니다"), 403
        data = request.get_json()
        region_name = data.get('region', '').strip()
        
        if not region_name:
            return jsonify({'error': '지역명을 입력하세요'}), 400
        
        try:
            deleted_counts = {}
            
            # 1. 검색 기록 삭제
            search_history_count = SearchHistory.query.filter_by(region=region_name).delete()
            deleted_counts['search_history'] = search_history_count
            
            # 2. 즐겨찾기 삭제
            favorite_count = Favorite.query.filter_by(region=region_name).delete()
            deleted_counts['favorites'] = favorite_count
            
            # 3. 리뷰 삭제
            review_count = Review.query.filter_by(region=region_name).delete()
            deleted_counts['reviews'] = review_count
            
            # 4. 신고 삭제
            report_count = Report.query.filter_by(region=region_name).delete()
            deleted_counts['reports'] = report_count
            
            # 5. 히트맵 데이터 삭제
            heatmap_count = HeatmapData.query.filter_by(region=region_name).delete()
            deleted_counts['heatmap_data'] = heatmap_count
            
            # 6. 실거래 데이터 삭제
            from sqlalchemy import or_
            real_tx_count = RealTransaction.query.filter(
                or_(
                    RealTransaction.region == region_name,
                    RealTransaction.dong_name.contains(region_name)
                )
            ).delete()
            deleted_counts['real_transactions'] = real_tx_count
            
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': f'{region_name} 지역 데이터가 삭제되었습니다.',
                'deleted_counts': deleted_counts
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'삭제 중 오류 발생: {str(e)}'}), 500
