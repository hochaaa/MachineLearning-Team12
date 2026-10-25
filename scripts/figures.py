"""ReportLab scientific bar charts from measured CSV (SVG; render to PNG with Sharp)."""
import csv
from pathlib import Path
from reportlab.graphics.shapes import Drawing, String, Rect
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics import renderSVG
from reportlab.lib import colors


def chart(path, title, categories, data, labels, ymax, ylabel, footnote):
    """Render labeled chart: data=series x category values; ymax declares axis scale."""
    drawing=Drawing(900,500)
    drawing.add(Rect(0,0,900,500,fillColor=colors.white,strokeColor=None))
    drawing.add(String(60,467,title,fontName='Helvetica-Bold',fontSize=20))
    drawing.add(String(60,438,ylabel,fontName='Helvetica',fontSize=12))
    bars=VerticalBarChart()
    bars.x,bars.y,bars.width,bars.height=75,85,755,320
    bars.data=data
    bars.categoryAxis.categoryNames=categories
    bars.valueAxis.valueMin=0
    bars.valueAxis.valueMax=ymax
    bars.valueAxis.valueStep=ymax/5
    palette=[colors.HexColor(x) for x in ['#245A81','#B87338','#547A4C','#986081']]
    for n,label in enumerate(labels):
        bars.bars[n].fillColor=palette[n]
        drawing.add(String(75+n*180,40,label,fillColor=palette[n],fontSize=12))
    bars.categoryAxis.labels.fontSize=11
    bars.valueAxis.labels.fontSize=10
    bars.barLabels.nudge=6
    bars.barLabelFormat='%.3f' if ymax<1 else '%d'
    bars.barLabels.fontSize=9
    drawing.add(bars)
    drawing.add(String(60,15,footnote,fontSize=9))
    renderSVG.drawToFile(drawing,str(path))


def main():
    directory=Path('outputs/figures');directory.mkdir(exist_ok=True)
    rows=list(csv.DictReader(open('outputs/audit/threshold_counts.csv')))
    chart(directory/'cohort_users.svg','Eligible users after conservative catalog alignment', ['>=3','>=4','>=5'],
          [[int(r['users']) for r in rows if r['zero_scenario']==p] for p in ('include','exclude')],
          ['Zero included','Zero excluded'],400,'Users (unique valid user-item pairs)',
          'Source: local Atrafshan + Fragrantica audit; zero policies are unresolved sensitivity scenarios.')
    rows=list(csv.DictReader(open('outputs/validation/metrics.csv')))
    for policy in ('include','exclude'):
        data=[]
        for method in ('popularity','content','mf','hybrid_0.25'):
            data.append([float(next(r['ndcg'] for r in rows if r['zero_scenario']==policy and r['threshold']==str(t)
                                    and r['grid']=='0' and r['method']==method)) for t in (3,4,5)])
        chart(directory/f'validation_{policy}.svg',f'Internal validation NDCG@10 with zero {policy}d',
              ['>=3','>=4','>=5'],data,['Popularity','Content','MF','Hybrid alpha=0.25'],.06,'Mean NDCG@10 (137 positive users)',
              'Source: development validation only; fixed 479 candidates; MF grid 0; provisional, no significance claim.')


if __name__=='__main__':main()
