import { writable, derived } from 'svelte/store';
import { get } from 'svelte/store';
import { is_login, access_token } from './store';
import fastapi from './api';

// 알림 상태 관리
export const notifications = writable([]);
export const unread_count = writable(0);
export const total_count = writable(0);

// 읽지 않은 알림만 필터링
export const unread_notifications = derived(
  notifications,
  $notifications => $notifications.filter(n => !n.is_read)
);

// 폴링 상태
let polling_interval = null;
const POLLING_INTERVAL = 10000; // 10초

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
