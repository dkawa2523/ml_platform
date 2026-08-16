# テストと品質検査

開発中は、変更ファイルの整形・lint、型検査、通常テストを実行します。

```powershell
uv run --group quality nox -s quality-fast
```

作業完了前は、architecture、branch coverage、securityを含むPR検査を実行します。

```powershell
uv run --group quality nox -s quality-pr
```

複数seed、CLI smoke、mutationはLinuxまたはWSL上のnightly検査に限定します。

```powershell
uv run --group nightly nox -s quality-nightly
```

ClearML Server／Agent接続を必要とするtemplate同期と実行確認は、ローカルテストとは分けて手動確認します。
