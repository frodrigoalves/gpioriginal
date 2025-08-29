$ErrorActionPreference="Stop"

# Branch base (troque para "main" se precisar)
$BASE="principal"

# Descobre "owner/repo" atual
$REPO = gh repo view --json owner,name --jq '"\(.owner.login)/\(.name)"'

function New-Issue {
  param([string]$Title,[string]$Body,[string]$Labels)
  gh api "repos/$REPO/issues" -f "title=$Title" -f "body=$Body" -f "labels=$Labels" --jq ".number"
}

function New-PR {
  param([int]$Issue,[string]$Type,[string]$Labels)

  git fetch origin $BASE
  git switch $BASE
  git pull --rebase

  $Title = gh issue view $Issue --json title --jq ".title"
  if (-not $Title) { throw "Issue #$Issue não encontrada." }

  $Slug = ($Title -replace '[^a-zA-Z0-9]+','-').ToLower().Trim('-')
  if ($Slug.Length -gt 30) { $Slug = $Slug.Substring(0,30) }
  $Branch = "$Type/issue-$Issue-$Slug"

  git switch -c $Branch

  # OBS: use ${var} antes de ":" para evitar o erro de variável inválida
  if (-not (git status --porcelain)) { git commit --allow-empty -m "$(${Type}): inicia trabalho da issue #$Issue" }
  git push -u origin $Branch

  gh pr create --base $BASE --head $Branch `
    --title "$(${Type}): $(${Title}) (#$Issue)" `
    --body "Closes #$Issue`n`nChecklist:`n- [ ] Implementação`n- [ ] Testes`n- [ ] Docs" `
    --label "$Labels" --draft

  gh pr edit --add-assignee @me
  gh pr merge --auto --squash
  Write-Host "PR criado e auto-merge ligado -> $Branch"
}

$tasks = @(
  @{ t="deps: adicionar React/Typescript p/ TSX";           k="chore"; l="codex,enhancement"; b="Adicionar react, react-dom, @types/react, @types/react-dom; ajustar scripts." },
  @{ t="sec: remover API key hardcoded (OpenFDA)";          k="sec";   l="codex,security";    b="Ler OPENFDA_KEY via env (backend/proxy) e remover literal do código." },
  @{ t="fix(api): limpar/implementar app.py e database.py"; k="fix";   l="codex,bug";         b="Substituir arquivos corrompidos por Flask funcional (healthz + /api/prescricao) ou remover se não usados." },
  @{ t="chore: remover/implementar stubs vazios";           k="chore"; l="codex,chore";       b="Excluir userService.ts/firebaseService.ts se não usados ou implementar mínimo + testes." },
  @{ t="guard: validar GEMINI_API_KEY no serviço Gemini";   k="fix";   l="codex,bug";         b="Checar GEMINI_API_KEY/GOOGLE_API_KEY antes de usar; falhar com mensagem clara." }
)

foreach ($x in $tasks) {
  $n = New-Issue -Title $x.t -Body $x.b -Labels $x.l
  New-PR -Issue $n -Type $x.k -Labels $x.l
}
Write-Host "`n Issues criadas e PRs (draft) abertos com auto-merge."
