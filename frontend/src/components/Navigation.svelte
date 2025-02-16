<script>
    import { link } from 'svelte-spa-router'
    import { page, keyword,access_token, username, is_login } from "../lib/store"

</script>

<!-- 네비게이션바 -->
<nav class="navbar navbar-expand-lg navbar-light bg-light border-bottom">
    <div class="container-fluid">
        <a use:link class="navbar-brand" href="/" on:click="{() => {$keyword = '', $page = 0}}">Pybo</a>
        <button
            class="navbar-toggler"
            type="button"
            data-bs-toggle="collapse"
            data-bs-target="#navbarSupportedContent"
            aria-controls="navbarSupportedContent"
            aria-expanded="false"
            aria-label="Toggle navigation">
            <span class="navbar-toggler-icon" />
        </button>
        <div class="collapse navbar-collapse" id="navbarSupportedContent">
            <ul class="navbar-nav me-auto mb-2 mb-lg-0">
                {#if $is_login }
                    <li class="nav-item">
                        <a use:link class="nav-link" href="/question-create">질문 등록</a>
                    </li>
                    <li class="nav-item">
                        <a use:link class="nav-link" href="/">{$username}</a>
                    </li>
                    <li class="nav-item">
                        <a use:link class="nav-link" href="/user-login" on:click={() => {
                            $access_token = ''
                            $username = ''
                            $is_login = false
                        }}>로그아웃</a>
                    </li>
                {:else}
                    <li class="nav-item">
                        <a use:link class="nav-link" href="/user-create">회원가입</a>
                    </li>
                    <li class="nav-item">
                        <a use:link class="nav-link" href="/user-login">로그인</a>
                    </li>
                {/if}
                <li class="nav-item">
                    <a use:link href="/performance-test" class="btn btn-outline-primary">일반 성능 테스트</a>
                    <a use:link href="/db-session-test" class="btn btn-outline-primary">DB 세션 테스트</a>
                </li>
            </ul>
        </div>
    </div>
</nav>