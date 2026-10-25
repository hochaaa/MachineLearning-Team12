"""Create evidence-based interim Word material; never replace the supplied proposal."""
from pathlib import Path
import csv
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


def table(document, headers, rows):
    """Create an auditable repeated-record table, flexible height and visible borders."""
    t=document.add_table(rows=1, cols=len(headers));t.style='Table Grid'
    for cell,text in zip(t.rows[0].cells,headers):cell.text=str(text)
    for row in rows:
        for cell,value in zip(t.add_row().cells,row):cell.text=str(value)
    for n,row in enumerate(t.rows):
        for cell in row.cells:
            shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'E5EAF0' if n==0 else 'FFFFFF');cell._tc.get_or_add_tcPr().append(shade)
            for p in cell.paragraphs:
                for run in p.runs:run.font.size=Pt(10)
    document.add_paragraph()


def main():
    doc=Document();sec=doc.sections[0]
    sec.top_margin=sec.bottom_margin=Inches(.7)
    sec.left_margin=sec.right_margin=Inches(.75)
    for name in ('Normal','Title','Heading 1','Heading 2'):
        style=doc.styles[name];style.font.name='Arial';style.font.color.rgb=RGBColor(0,0,0)
    doc.styles['Normal'].font.size=Pt(10.5)
    doc.styles['Normal'].paragraph_format.space_after=Pt(5)
    doc.add_heading('Personalized Perfume Recommendation System',0)
    doc.add_paragraph('Team 12   김동은 · 박찬민 · 이호찬\nDevelopment evidence as of 22 October 2026')
    doc.add_paragraph('The local system implements content recommendation, SGD matrix factorization, weighted hybrid scoring and explicit scent rules. Real internal validation is complete for both zero-rating assumptions. The final zero policy and internal and external test assessments remain blocked. This document is interim Word material for team review.')
    doc.add_heading('Requirements and implementation',1)
    doc.add_paragraph('The professor specification requires at least two filtering categories, independent development and testing datasets, a Word proposal, a final presentation with code and outputs, architecture, authentic individual learning and contribution information, and a GitHub URL. Hybrid and a method beyond the course were reported as verbal requirements. MF, knowledge rules and the 3/4/5 comparison follow the final proposal and user instructions. No numerical accuracy target or web interface is required by the slides.')
    doc.add_heading('Observed source data',1)
    table(doc,['Source','Observed evidence','Role'],[
      ['Fragrantica','24,063 catalog rows','Development content'],
      ['Atrafshan','6,882 scent scores, including 1,309 zeros','Development interactions'],
      ['Laure / Basenotes','6,288 reviews, 2,694 rated perfumes','External assessment pending'],
      ['Parfumo','Available locally, auxiliary analysis pending','Metadata cross-check only']])
    doc.add_paragraph('Raw input files remain unchanged and private. Input hashes, schema information and matching records are saved under outputs/audit. The user confirmed classroom local analysis and training permission on 22 October. This confirmation does not authorize redistribution.')
    doc.add_page_break()
    doc.add_heading('Zero-rating audit and cohort sizes',1)
    doc.add_paragraph('All 1,309 zero-scent records contain a nonzero score in another aspect. Bottle design is also zero in 1,302 of them. The original README and paper do not explicitly establish zero as an unrated sentinel. No collection or zero-conversion code was found in the inspected public folders. Both interpretations remain provisional.')
    rows=list(csv.DictReader(open('outputs/audit/threshold_counts.csv')))
    table(doc,['Zero','Minimum','Users','Items','Ratings'],[[r['zero_scenario'],r['threshold'],r['users'],r['items'],r['interactions']] for r in rows])
    doc.add_picture('outputs/figures/cohort_users.png',width=Inches(6.2))
    doc.add_paragraph('Counts are after conservative brand and name alignment, before splitting. Zero-excluded >=5 has 291 users before alignment and 168 after alignment. The earlier 177-user observation was not reproduced. EDT, EDP, Elixir and version terms are preserved. Ambiguous matches remain excluded and accepted matches still require semantic review.')
    doc.add_page_break()
    doc.add_heading('Frozen validation protocol',1)
    doc.add_paragraph('The nonzero >=5 cohort supplies 168 common users. One validation and one internal-test observation per user are assigned by a deterministic identity hash, leaving at least three training observations. Additional lower-activity users enter training only. Both zero assumptions and all three thresholds share validation labels and the same 479-item candidate universe. No internal or external test metrics were computed.')
    doc.add_paragraph('Observed ratings >=7/10 are relevant. The 137 users with a positive validation observation contribute to ranking averages. The other 31 are reported separately. Fifteen positive labels outside the common candidate pool remain misses. Unobserved candidates are not assigned negative training labels. Precision uses K=10 and recall uses all observed positive labels.')
    doc.add_heading('Internal validation results',1)
    metrics=list(csv.DictReader(open('outputs/validation/metrics.csv')))
    values=[]
    for policy in ('include','exclude'):
        for threshold in ('3','4','5'):
            chosen={r['method']:float(r['ndcg']) for r in metrics if r['zero_scenario']==policy and r['threshold']==threshold and r['grid']=='0'}
            values.append([policy,threshold]+[f'{chosen[m]:.5f}' for m in ('popularity','content','mf','hybrid_0.25')])
    table(doc,['Zero','Min','Popular','Content','MF','Hybrid .25'],values)
    doc.add_picture('outputs/figures/validation_exclude.png',width=Inches(6.2))
    doc.add_paragraph('Table and plot use MF grid 0 consistently. Over the complete two-setting MF grid and three alpha weights, provisional hybrid selection is zero-included >=4, alpha .25, NDCG@10 .0343659, or zero-excluded >=5, alpha .25, NDCG@10 .0404023. The zero policy itself is not selected. Large per-user variation and small hit counts prevent claims of significant improvement. MF ranks below popularity in these settings.')
    doc.add_page_break()
    doc.add_heading('Models and software architecture',1)
    doc.add_paragraph('Private raw files feed adapters and conservative catalog matching, then persisted train and validation manifests. Train-only binary TF-IDF vectors support cosine profiles. A bias-free MF model learns user and item vectors by SGD with per-observation L2. Explicit predictions are clipped to the declared 0–1 scale. Hybrid combines content cosine and MF prediction at a validation-selected weight, with documented component and popularity fallbacks.')
    doc.add_paragraph('Hard rules require every selected note or accord and reject forbidden tokens. Soft preferred-token matches can add a bounded bonus before ranking. Woody, floral and rose rules each returned 1,680 of 1,680 compliant results over 168 development users. This measures rule satisfaction, not personalized preference accuracy. Season and price are disabled because reliable development fields are absent.')
    doc.add_paragraph('For new users, ridge fold-in estimates a new user vector using support ratings only, with development item factors fixed. Scoring receives no answer item identities or values. Unknown factor items fall back explicitly. See src/perfume, METHODS_EXPLAINED.md and reports/API_REFERENCE.md for equations, parameter definitions and library explanations.')
    doc.add_heading('External feasibility and limitations',1)
    table(doc,['Provisional model','Factor overlap items','Reviews','Users >=2'],[
        ['Zero included',67,455,62],['Zero excluded',63,428,54]])
    doc.add_paragraph('These counts use review identities only and the actual trained factor catalog. Content matching reaches 836 rated source perfumes and 2,437 unique interactions. They do not establish enough positive held-out labels or compatible rating semantics. Two conflicting Laure rows share one primary key and are quarantined, leaving 39,697 usable catalog IDs from 39,699 rows. Final support and answer policy, rating-scale mapping and the frozen external run are pending.')
    doc.add_heading('Verification and remaining team inputs',1)
    doc.add_paragraph('Synthetic tests cover zero-policy gating, conflicting pairs, concentration collisions, split reproducibility, common validation, train-only vocabulary, MF learning, fixed-factor ridge fold-in, cold start, knowledge rules, ranking formulas, answer isolation and foreign keys. Persisted real-data checks confirm disjoint labels and monotone training expansion. Commands and logs are in reports/STATUS.md.')
    doc.add_paragraph('The team must decide the zero policy, review matching, confirm which method is beyond the course, and provide authentic roles, contribution percentages and individual learning. A verified GitHub URL, exact presentation date and final Word expectations remain TBD. The existing proposal is preserved without modification. Final submission is due 9 November, followed by a 10-minute presentation and 3-minute Q&A on 10 or 12 November.')
    doc.add_heading('Sources',1)
    doc.add_paragraph('Professor Ok-Ran Jeong, Term Project Specification, Fall 2026, pages 2–9. Team12 final supplied proposal. Atrafshan source: github.com/Kalashi-Saed-Collaborations/SentimentDrivenCommunityDetection. Kalashi et al., Applied Network Science 11, 13 (2026), doi:10.1007/s41109-025-00757-0. Remaining dataset links, permission observations and dependency provenance appear in REFERENCES.md. No external implementation code was copied.')
    Path('reports/drafts').mkdir(exist_ok=True)
    for style in doc.styles:
        for border in list(style.element.iter(qn('w:pBdr'))):
            border.getparent().remove(border)
    for paragraph in doc.paragraphs:
        for border in list(paragraph._p.iter(qn('w:pBdr'))):
            border.getparent().remove(border)
        for run in paragraph.runs:
            if any('가' <= char <= '힣' for char in run.text):
                run.font.name='AppleGothic'
                run._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'AppleGothic')
    doc.save('reports/drafts/Team12_Development_Report.docx')


if __name__=='__main__':main()
