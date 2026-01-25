"""train コマンド - MLモデルを学習して保存する"""

from datetime import date
from datetime import datetime as dt

import click
import numpy as np

from keiba.db import get_engine, get_session
from keiba.ml.feature_builder import FeatureBuilder
from keiba.ml.trainer import Trainer as MLTrainer
from keiba.services.training_service import build_training_data


@click.command()
@click.option("--db", required=True, type=click.Path(exists=True), help="データベースファイルパス")
@click.option("--output", required=True, type=click.Path(), help="出力モデルパス")
@click.option("--cutoff-date", default=None, help="学習データのカットオフ日（YYYY-MM-DD）")
def train(db: str, output: str, cutoff_date: str | None):
    """MLモデルを学習して保存する"""
    click.echo("学習開始")
    click.echo(f"データベース: {db}")
    click.echo(f"出力先: {output}")

    # カットオフ日付をパース
    if cutoff_date is not None:
        try:
            target_date = dt.strptime(cutoff_date, "%Y-%m-%d").date()
        except ValueError:
            click.echo(f"日付形式が不正です: {cutoff_date}（YYYY-MM-DD形式で指定してください）")
            raise SystemExit(1)
    else:
        # カットオフ日付が指定されていない場合は今日を使用
        target_date = date.today()

    click.echo(f"カットオフ日付: {target_date}")
    click.echo("")

    # DBに接続
    engine = get_engine(db)

    with get_session(engine) as session:
        # 学習データを構築
        click.echo("学習データを構築中...")
        features_list, labels = build_training_data(session, target_date)
        training_count = len(features_list)

        if training_count < 100:
            click.echo(f"学習データ不足（{training_count}サンプル）: 最低100サンプル必要")
            raise SystemExit(1)

        click.echo(f"学習データ: {training_count}サンプル")

        # 特徴量行列を作成
        feature_builder = FeatureBuilder()
        feature_names = feature_builder.get_feature_names()
        X = np.array([[f[name] for name in feature_names] for f in features_list])
        y = np.array(labels)

        # モデルを学習
        click.echo("モデルを学習中...")
        trainer = MLTrainer()
        metrics = trainer.train_with_cv(X, y, n_splits=5)

        # メトリクスを表示
        click.echo("")
        click.echo("学習完了")
        if metrics.get("precision_at_1") is not None:
            click.echo(f"  Precision@1: {metrics['precision_at_1']:.1%}")
        if metrics.get("precision_at_3") is not None:
            click.echo(f"  Precision@3: {metrics['precision_at_3']:.1%}")
        if metrics.get("auc_roc") is not None:
            click.echo(f"  AUC-ROC: {metrics['auc_roc']:.3f}")

        # モデルを保存
        trainer.save_model(output)
        click.echo("")
        click.echo(f"モデルを保存しました: {output}")
