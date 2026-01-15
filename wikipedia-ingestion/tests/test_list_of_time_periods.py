from pathlib import Path
from bs4 import BeautifulSoup

from strategies.list_of_time_periods.list_of_time_periods_strategy import ListOfTimePeriodsStrategy


def test_extract_events_from_section_handles_nested_uls():
    html = """
    <html><body>
      <h2 id="African_periods">African periods</h2>
      <div>
        <h3>Egyptian periods</h3>
        <div class="link">
          <ul>
            <li>Early Dynastic Period (3150 BC – 2686 BC)</li>
            <li>Old Kingdom (2686 BC – 2181 BC)</li>
          </ul>
        </div>
        <h3>Libyan periods</h3>
        <div class="link">
          <ul>
            <li>Libyan Period (1000 BC – 800 BC)</li>
          </ul>
        </div>
      </div>
      <h2 id="American_periods">American (continent) periods</h2>
    </body></html>
    """

    soup = BeautifulSoup(html, 'html.parser')
    heading = soup.find(id='African_periods')

    strategy = ListOfTimePeriodsStrategy(run_id='test', output_dir=Path('.'))
    events = strategy._extract_events_from_section(soup, heading, 'African periods')

    assert len(events) == 3
    titles = [e.title for e in events]
    assert any('Early Dynastic' in t for t in titles)
    assert any('Old Kingdom' in t for t in titles)
    assert any('Libyan Period' in t for t in titles)
