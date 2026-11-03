<script>
  import { link } from "svelte-spa-router";
  import {
    unread_count,
    notifications,
    connection_status,
    connection_mode,
    markAsRead,
    getNotificationIcon,
  } from "../lib/notification";
  import { onMount } from "svelte";

  let show_dropdown = false;
  let recent_notifications = [];

  // 최근 5개 알림만 표시
  $: recent_notifications = $notifications.slice(0, 5);

  function toggleDropdown() {
    show_dropdown = !show_dropdown;
  }

  function closeDropdown() {
    show_dropdown = false;
  }

  function handleMarkAsRead(notification_id) {
    markAsRead([notification_id]);
  }

  // 외부 클릭 시 드롭다운 닫기
  function handleClickOutside(event) {
    const dropdown = document.getElementById("notification-dropdown");
    if (dropdown && !dropdown.contains(event.target)) {
      show_dropdown = false;
    }
  }

  onMount(() => {
    document.addEventListener("click", handleClickOutside);
    return () => {
      document.removeEventListener("click", handleClickOutside);
    };
  });
</script>

<div class="notification-bell" id="notification-dropdown">
  <!-- 알림 벨 아이콘 -->
  <button
    class="btn btn-link position-relative"
    on:click|stopPropagation={toggleDropdown}
    aria-label="알림"
  >
    <span class="fs-4">🔔</span>
    {#if $unread_count > 0}
      <span
        class="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger"
      >
        {$unread_count > 99 ? "99+" : $unread_count}
        <span class="visually-hidden">읽지 않은 알림</span>
      </span>
    {/if}

    <!-- 연결 상태 인디케이터 -->
    {#if $connection_mode === 'sse' && $connection_status === 'connected'}
      <span class="connection-indicator connection-online" title="실시간 연결됨"></span>
    {:else if $connection_mode === 'sse' && $connection_status === 'connecting'}
      <span class="connection-indicator connection-connecting" title="연결 중..."></span>
    {:else if $connection_mode === 'polling'}
      <span class="connection-indicator connection-polling" title="폴링 모드"></span>
    {/if}
  </button>

  <!-- 드롭다운 -->
  {#if show_dropdown}
    <div class="notification-dropdown card shadow">
      <div class="card-header">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <h6 class="mb-0">알림</h6>
          <a
            use:link
            href="/notifications"
            class="btn btn-sm btn-outline-primary"
            on:click={closeDropdown}
          >
            전체보기
          </a>
        </div>
        <!-- 연결 상태 -->
        <div class="text-muted small">
          {#if $connection_mode === 'sse' && $connection_status === 'connected'}
            <span class="text-success">● 실시간 연결됨</span>
          {:else if $connection_mode === 'sse' && $connection_status === 'connecting'}
            <span class="text-warning">● 연결 중...</span>
          {:else if $connection_mode === 'polling'}
            <span class="text-info">● 폴링 모드 (10초)</span>
          {:else}
            <span class="text-secondary">● 연결 없음</span>
          {/if}
        </div>
      </div>
      <div class="card-body p-0">
        {#if recent_notifications.length === 0}
          <div class="text-center py-4 text-muted">알림이 없습니다</div>
        {:else}
          <ul class="list-group list-group-flush">
            {#each recent_notifications as notification}
              <li
                class="list-group-item {notification.is_read
                  ? ''
                  : 'bg-light'} notification-item"
              >
                <div class="d-flex justify-content-between align-items-start">
                  <div class="flex-grow-1">
                    <div class="d-flex align-items-center mb-1">
                      <span class="me-2"
                        >{getNotificationIcon(notification.event_type)}</span
                      >
                      <small class="text-muted"
                        >{new Date(
                          notification.created_at
                        ).toLocaleString()}</small
                      >
                    </div>
                    <p class="mb-0 small">{notification.message}</p>
                  </div>
                  {#if !notification.is_read}
                    <button
                      class="btn btn-sm btn-link p-0 ms-2"
                      on:click={() => handleMarkAsRead(notification.id)}
                      title="읽음 처리"
                    >
                      ✓
                    </button>
                  {/if}
                </div>
              </li>
            {/each}
          </ul>
        {/if}
      </div>
    </div>
  {/if}
</div>

<style>
  .notification-bell {
    position: relative;
  }

  .notification-dropdown {
    position: absolute;
    top: 100%;
    right: 0;
    width: 350px;
    max-height: 500px;
    overflow-y: auto;
    z-index: 1050;
    margin-top: 0.5rem;
  }

  .notification-item {
    cursor: pointer;
    transition: background-color 0.2s;
  }

  .notification-item:hover {
    background-color: #f8f9fa !important;
  }

  /* 연결 상태 인디케이터 */
  .connection-indicator {
    position: absolute;
    bottom: 0;
    right: 0;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    border: 2px solid white;
  }

  .connection-online {
    background-color: #28a745;
    animation: pulse-indicator 2s infinite;
  }

  .connection-connecting {
    background-color: #ffc107;
    animation: blink-indicator 1s infinite;
  }

  .connection-polling {
    background-color: #17a2b8;
  }

  @keyframes pulse-indicator {
    0%, 100% {
      opacity: 1;
      transform: scale(1);
    }
    50% {
      opacity: 0.7;
      transform: scale(1.1);
    }
  }

  @keyframes blink-indicator {
    0%, 50%, 100% {
      opacity: 1;
    }
    25%, 75% {
      opacity: 0.3;
    }
  }

  @media (max-width: 576px) {
    .notification-dropdown {
      width: 300px;
      right: -50px;
    }
  }
</style>
