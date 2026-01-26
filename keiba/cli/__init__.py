"""Click CLIメインモジュール"""

import click

# 後方互換性のための再エクスポート: formatters/markdown.py
from keiba.cli.formatters.markdown import (
    save_predictions_markdown,
    parse_predictions_markdown,
    append_review_to_markdown,
)
# 旧名（_ 付き）のエイリアス
_save_predictions_markdown = save_predictions_markdown
_parse_predictions_markdown = parse_predictions_markdown
_append_review_to_markdown = append_review_to_markdown

# 後方互換性のための再エクスポート: formatters/simulation.py
from keiba.cli.formatters.simulation import (
    calculate_fukusho_simulation,
    calculate_tansho_simulation,
    calculate_umaren_simulation,
    calculate_sanrenpuku_simulation,
)
# 旧名（_ 付き）のエイリアス
_calculate_fukusho_simulation = calculate_fukusho_simulation
_calculate_tansho_simulation = calculate_tansho_simulation
_calculate_umaren_simulation = calculate_umaren_simulation
_calculate_sanrenpuku_simulation = calculate_sanrenpuku_simulation

# 後方互換性のための再エクスポート: utils/url_parser.py
from keiba.cli.utils.url_parser import (
    extract_race_id_from_url,
    extract_race_id_from_shutuba_url,
)

# 後方互換性のための再エクスポート: utils/date_parser.py
from keiba.cli.utils.date_parser import parse_race_date

# 後方互換性のための再エクスポート: utils/table_printer.py
from keiba.cli.utils.table_printer import (
    print_score_table,
    print_score_table_with_ml,
    print_prediction_table,
)
# 旧名（_ 付き）のエイリアス
_print_score_table = print_score_table
_print_score_table_with_ml = print_score_table_with_ml
_print_prediction_table = print_prediction_table

# 後方互換性のための再エクスポート: db
from keiba.db import get_engine, get_session, init_db

# 後方互換性のための再エクスポート: scrapers
from keiba.scrapers import RaceDetailScraper, RaceListScraper, HorseDetailScraper


@click.group()
def main():
    """競馬データ収集・分析CLI"""
    pass


# コマンドの登録
from keiba.cli.commands.scrape import scrape, scrape_horses
from keiba.cli.commands.analyze import analyze
from keiba.cli.commands.predict import predict, predict_day
from keiba.cli.commands.train import train
from keiba.cli.commands.review import review_day
from keiba.cli.commands.backtest import (
    backtest,
    backtest_fukusho,
    backtest_tansho,
    backtest_umaren,
    backtest_sanrenpuku,
)
from keiba.cli.commands.migrate import migrate_grades

main.add_command(scrape)
main.add_command(scrape_horses)
main.add_command(analyze)
main.add_command(predict)
main.add_command(predict_day)
main.add_command(train)
main.add_command(review_day)
main.add_command(backtest)
main.add_command(backtest_fukusho)
main.add_command(backtest_tansho)
main.add_command(backtest_umaren)
main.add_command(backtest_sanrenpuku)
main.add_command(migrate_grades)


__all__ = [
    "main",
    # formatters/markdown.py
    "save_predictions_markdown",
    "parse_predictions_markdown",
    "append_review_to_markdown",
    # formatters/simulation.py
    "calculate_fukusho_simulation",
    "calculate_tansho_simulation",
    "calculate_umaren_simulation",
    "calculate_sanrenpuku_simulation",
    # utils/url_parser.py
    "extract_race_id_from_url",
    "extract_race_id_from_shutuba_url",
    # utils/date_parser.py
    "parse_race_date",
    # utils/table_printer.py
    "print_score_table",
    "print_score_table_with_ml",
    "print_prediction_table",
    # db
    "get_engine",
    "get_session",
    "init_db",
    # scrapers
    "RaceDetailScraper",
    "RaceListScraper",
    "HorseDetailScraper",
]
