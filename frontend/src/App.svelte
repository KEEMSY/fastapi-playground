<script>
  import Router from "svelte-spa-router";
  import Home from "./routes/Home.svelte";
  import Detail from "./routes/Detail.svelte";
  import QuestionCreate from "./routes/QuestionCreate.svelte";
  import Navigation from "./components/Navigation.svelte";
  import UserCreate from "./routes/UserCreate.svelte";
  import UserLogin from "./routes/UserLogin.svelte";
  import QuestionModify from "./routes/QuestionModify.svelte";
  import AnswerModify from "./routes/AnswerModify.svelte";
  import PerformanceTest from "./routes/PerformanceTest.svelte";
  import DbSessionTest from "./routes/DbSessionTest.svelte";
  import ProductionTest from "./routes/ProductionTest.svelte";

  const routes = {
    "/": Home,
    "/detail/:question_id": Detail,
    "/question-create": QuestionCreate,
    "/user-create": UserCreate,
    "/user-login": UserLogin,
    "/question-modify/:question_id": QuestionModify,
    "/answer-modify/:answer_id": AnswerModify,
    "/performance-test": PerformanceTest,
    "/db-session-test": DbSessionTest,
    "/production-test": ProductionTest,
  };
</script>

<Navigation />
<Router {routes} />
