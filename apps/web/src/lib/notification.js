import { writable, derived } from 'svelte/store';
import { get } from 'svelte/store';
import { is_login, access_token } from './store';
import fastapi from './api';

// 알림 상태 관리
export const notifications = writable([]);
export const unread_count = writable(0);
export const total_count = writable(0);

// SSE 연결 상태 관리
export const connection_status = writable('disconnected'); // connecting, connected, disconnected, error
export const connection_mode = writable('none'); // sse, polling, none

// 읽지 않은 알림만 필터링
export const unread_notifications = derived(
  notifications,
  $notifications => $notifications.filter(n => !n.is_read)
);

// 폴링 상태
let polling_interval = null;
const POLLING_INTERVAL = 10000; // 10초

// SSE 연결 상태
let eventSource = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 3000;
const SSE_ENABLED = true; // SSE 기능 토글 (false로 설정하면 폴링 모드로 전환)

/**
 * 알림 목록 조회
 */
export function fetchNotifications(page = 0, size = 20) {
  if (!get(is_login)) {
    return;
  }

  fastapi('get', '/api/notification/list', { page, size }, (response) => {
    notifications.set(response.notifications || []);
    unread_count.set(response.unread_count || 0);
    total_count.set(response.total || 0);
  });
}

/**
 * 선택한 알림을 읽음 처리
 */
export function markAsRead(notification_ids, callback) {
  fastapi(
    'put',
    '/api/notification/read',
    { notification_ids },
    () => {
      // 로컬 상태 업데이트
      notifications.update(list =>
        list.map(n =>
          notification_ids.includes(n.id) ? { ...n, is_read: true } : n
        )
      );
      unread_count.update(count => Math.max(0, count - notification_ids.length));
      if (callback) callback();
    }
  );
}

/**
 * 모든 알림을 읽음 처리
 */
export function markAllAsRead(callback) {
  fastapi('put', '/api/notification/read-all', {}, () => {
    // 로컬 상태 업데이트
    notifications.update(list =>
      list.map(n => ({ ...n, is_read: true }))
    );
    unread_count.set(0);
    if (callback) callback();
  });
}

/**
 * 알림 폴링 시작
 */
export function startNotificationPolling() {
  if (polling_interval) {
    return; // 이미 실행 중
  }

  connection_status.set('connected');
  connection_mode.set('polling');

  // 즉시 1회 실행
  fetchNotifications();

  // 주기적으로 실행
  polling_interval = setInterval(() => {
    if (get(is_login)) {
      fetchNotifications();
    } else {
      stopNotificationPolling();
    }
  }, POLLING_INTERVAL);

  console.log('✅ 알림 폴링 시작 (10초 간격)');
}

/**
 * 알림 폴링 중지
 */
export function stopNotificationPolling() {
  if (polling_interval) {
    clearInterval(polling_interval);
    polling_interval = null;
    console.log('🛑 알림 폴링 중지');
  }

  // 상태 초기화
  notifications.set([]);
  unread_count.set(0);
  total_count.set(0);
  connection_status.set('disconnected');
  connection_mode.set('none');
}

/**
 * 알림 타입별 아이콘
 */
export function getNotificationIcon(event_type) {
  const icons = {
    question_voted: '👍',
    answer_created: '💬',
    answer_voted: '👍',
  };
  return icons[event_type] || '🔔';
}

/**
 * 알림 타입별 색상
 */
export function getNotificationColor(event_type) {
  const colors = {
    question_voted: 'primary',
    answer_created: 'success',
    answer_voted: 'info',
  };
  return colors[event_type] || 'secondary';
}

/**
 * SSE 연결 시작
 */
export function startNotificationSSE() {
  if (!get(is_login) || !SSE_ENABLED) {
    // SSE 비활성화 또는 미로그인 시 폴링 모드로 전환
    startNotificationPolling();
    return;
  }

  const token = get(access_token);
  if (!token) {
    console.warn('⚠️ 토큰 없음, 폴링 모드로 전환');
    startNotificationPolling();
    return;
  }

  // 기존 연결 종료
  stopNotificationSSE();
  stopNotificationPolling(); // 폴링 중지

  try {
    connection_status.set('connecting');
    connection_mode.set('sse');

    const baseUrl = import.meta.env.VITE_SERVER_URL || 'http://localhost:8000';
    const url = `${baseUrl}/api/notification/stream?token=${token}`;

    eventSource = new EventSource(url);

    // 연결 성공
    eventSource.addEventListener('connected', (e) => {
      const data = JSON.parse(e.data);
      console.log('✅ SSE 연결 성공', data);
      reconnectAttempts = 0;
      connection_status.set('connected');

      // 초기 알림 목록 로드
      fetchNotifications();
    });

    // 새 알림 수신
    eventSource.addEventListener('notification', (e) => {
      const notification = JSON.parse(e.data);
      console.log('🔔 새 알림:', notification);

      // 상태 업데이트 (최상단에 추가)
      notifications.update(list => [notification, ...list]);
      unread_count.update(count => count + 1);
      total_count.update(count => count + 1);
    });

    // Heartbeat
    eventSource.addEventListener('heartbeat', () => {
      console.log('💓 Heartbeat');
    });

    // 에러 처리
    eventSource.onerror = (error) => {
      console.error('❌ SSE 에러:', error);
      connection_status.set('error');

      if (eventSource.readyState === EventSource.CLOSED) {
        connection_status.set('disconnected');
        handleSSEReconnect();
      }
    };

  } catch (error) {
    console.error('❌ SSE 연결 실패:', error);
    connection_status.set('error');
    startNotificationPolling();
  }
}

/**
 * SSE 재연결 로직
 */
function handleSSEReconnect() {
  if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
    console.warn('⚠️ SSE 재연결 실패, 폴링 모드로 전환');
    stopNotificationSSE();
    startNotificationPolling();
    return;
  }

  reconnectAttempts++;
  connection_status.set('connecting');
  console.log(`🔄 SSE 재연결 시도 ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS}...`);

  setTimeout(() => {
    if (get(is_login)) {
      startNotificationSSE();
    }
  }, RECONNECT_DELAY);
}

/**
 * SSE 연결 종료
 */
export function stopNotificationSSE() {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
    console.log('🛑 SSE 연결 종료');
  }
  reconnectAttempts = 0;
  connection_status.set('disconnected');
  connection_mode.set('none');
}
