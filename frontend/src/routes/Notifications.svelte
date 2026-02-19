<script>
  import {
    notifications,
    unread_count,
    total_count,
    fetchNotifications,
    markAsRead,
    markAllAsRead,
    getNotificationIcon,
    getNotificationColor,
  } from "../lib/notification";
  import { onMount } from "svelte";

  let page = 0;
  let size = 20;
  let selected_ids = new Set();
  let filter_type = "all"; // all, unread, read

  $: filtered_notifications =
    filter_type === "all"
      ? $notifications
      : filter_type === "unread"
      ? $notifications.filter((n) => !n.is_read)
      : $notifications.filter((n) => n.is_read);

  onMount(() => {
    fetchNotifications(page, size);
  });

  function handleSelectAll() {
    if (selected_ids.size === filtered_notifications.length) {
      selected_ids = new Set();
    } else {
      selected_ids = new Set(filtered_notifications.map((n) => n.id));
    }
  }

  function handleToggleSelect(id) {
    if (selected_ids.has(id)) {
      selected_ids.delete(id);
    } else {
      selected_ids.add(id);
    }
    selected_ids = selected_ids; // trigger reactivity
  }

  function handleMarkSelectedAsRead() {
    if (selected_ids.size === 0) {
      alert("읽음 처리할 알림을 선택하세요.");
      return;
    }

    markAsRead(Array.from(selected_ids), () => {
      selected_ids = new Set();
      alert("선택한 알림을 읽음 처리했습니다.");
    });
  }

  function handleMarkAllAsRead() {
    if (
      confirm(
        `모든 알림(${$unread_count}개)을 읽음 처리하시겠습니까?`
      )
    ) {
      markAllAsRead(() => {
        selected_ids = new Set();
        alert("모든 알림을 읽음 처리했습니다.");
      });
    }
  }

  function handleRefresh() {
    fetchNotifications(page, size);
  }

  function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;

    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return "방금 전";
    if (minutes < 60) return `${minutes}분 전`;
    if (hours < 24) return `${hours}시간 전`;
    if (days < 7) return `${days}일 전`;

    return date.toLocaleDateString("ko-KR");
  }
</script>

<div class="container my-4">
  <div class="row mb-4">
    <div class="col-12">
      <div class="d-flex justify-content-between align-items-center">
        <h2>
          🔔 알림
          {#if $unread_count > 0}
            <span class="badge bg-danger">{$unread_count}</span>
          {/if}
        </h2>
        <button class="btn btn-outline-secondary btn-sm" on:click={handleRefresh}>
          🔄 새로고침
        </button>
      </div>
    </div>
  </div>

  <!-- 필터 및 액션 버튼 -->
  <div class="row mb-3">
    <div class="col-md-6">
      <div class="btn-group" role="group">
        <button
          type="button"
          class="btn btn-sm {filter_type === 'all'
            ? 'btn-primary'
            : 'btn-outline-primary'}"
          on:click={() => (filter_type = "all")}
        >
          전체 ({$total_count})
        </button>
        <button
          type="button"
          class="btn btn-sm {filter_type === 'unread'
            ? 'btn-primary'
            : 'btn-outline-primary'}"
          on:click={() => (filter_type = "unread")}
        >
          읽지 않음 ({$unread_count})
        </button>
        <button
          type="button"
          class="btn btn-sm {filter_type === 'read'
            ? 'btn-primary'
            : 'btn-outline-primary'}"
          on:click={() => (filter_type = "read")}
        >
          읽음 ({$total_count - $unread_count})
        </button>
      </div>
    </div>
    <div class="col-md-6 text-end">
      <button
        class="btn btn-sm btn-outline-primary me-2"
        on:click={handleMarkSelectedAsRead}
        disabled={selected_ids.size === 0}
      >
        선택 읽음 처리 ({selected_ids.size})
      </button>
      <button
        class="btn btn-sm btn-outline-danger"
        on:click={handleMarkAllAsRead}
        disabled={$unread_count === 0}
      >
        전체 읽음 처리
      </button>
    </div>
  </div>

  <!-- 알림 목록 -->
  {#if filtered_notifications.length === 0}
    <div class="text-center py-5">
      <p class="text-muted fs-5">알림이 없습니다</p>
    </div>
  {:else}
    <div class="mb-3">
      <input
        type="checkbox"
        id="select-all"
        class="form-check-input me-2"
        checked={selected_ids.size === filtered_notifications.length &&
          filtered_notifications.length > 0}
        on:change={handleSelectAll}
      />
      <label for="select-all" class="form-check-label small">
        전체 선택
      </label>
    </div>

    <div class="list-group">
      {#each filtered_notifications as notification (notification.id)}
        <div
          class="list-group-item {notification.is_read ? '' : 'list-group-item-light'}"
        >
          <div class="d-flex">
            <!-- 체크박스 -->
            <div class="me-3">
              <input
                type="checkbox"
                class="form-check-input mt-2"
                checked={selected_ids.has(notification.id)}
                on:change={() => handleToggleSelect(notification.id)}
              />
            </div>

            <!-- 알림 내용 -->
            <div class="flex-grow-1">
              <div class="d-flex align-items-center mb-2">
                <span class="fs-4 me-2"
                  >{getNotificationIcon(notification.event_type)}</span
                >
                <span
                  class="badge bg-{getNotificationColor(
                    notification.event_type
                  )} me-2"
                >
                  {notification.event_type}
                </span>
                {#if !notification.is_read}
                  <span class="badge bg-danger me-2">NEW</span>
                {/if}
                <small class="text-muted"
                  >{formatDate(notification.created_at)}</small
                >
              </div>

              <p class="mb-2">{notification.message}</p>

              {#if notification.actor}
                <div class="d-flex align-items-center">
                  <small class="text-muted">
                    👤 {notification.actor.username}
                  </small>
                  <small class="text-muted ms-3">
                    📌 {notification.resource_type} #{notification.resource_id}
                  </small>
                </div>
              {/if}
            </div>

            <!-- 읽음 처리 버튼 -->
            {#if !notification.is_read}
              <div class="ms-3">
                <button
                  class="btn btn-sm btn-outline-primary"
                  on:click={() =>
                    markAsRead([notification.id], () => {
                      selected_ids.delete(notification.id);
                      selected_ids = selected_ids;
                    })}
                >
                  ✓ 읽음
                </button>
              </div>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}

  <!-- 폴링 상태 표시 -->
  <div class="mt-4 text-center text-muted small">
    <p>
      💡 알림은 10초마다 자동으로 확인됩니다.
      <br />
      마지막 업데이트: {new Date().toLocaleTimeString()}
    </p>
  </div>
</div>

<style>
  .list-group-item {
    transition: all 0.2s;
  }

  .list-group-item:hover {
    background-color: #f8f9fa;
  }

  .list-group-item-light {
    background-color: #e7f3ff;
  }
</style>
