from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import InvalidSessionIdException, WebDriverException, ElementClickInterceptedException

import pandas as pd
import time
import datetime
import warnings
from bs4 import BeautifulSoup
from selenium.common.exceptions import StaleElementReferenceException
warnings.filterwarnings('ignore')

chrome_options = webdriver.ChromeOptions()
chrome_options.add_experimental_option("detach", True)   # 끝나도 창 유지
chrome_options.add_argument('--start-maximized')

driver = webdriver.Chrome(options=chrome_options)

url = "https://www.wanted.co.kr/search?query=unreal&tab=position"
url = "https://www.wanted.co.kr/wdlist"

#url = "https://www.wanted.co.kr/wdlist/518/10531"   #3건
#url = "https://www.wanted.co.kr/wdlist/518/10536"   #7건  테크니털 라이터터
#url = "https://www.wanted.co.kr/wdlist/518/10110"  #소프트웨어 개발자 900간
url = "https://www.wanted.co.kr/wdlist/518/899"   #파이썬 개발자자  400건


driver.get(url)

# 페이지 로딩 대기
time.sleep(3)

# 실제 HTML 구조에 맞는 XPath 사용
# data-cy="job-card"를 가진 div 내부의 a 태그 선택
element_xpath = "//div[@data-cy='job-card']/a"

# 대체 선택자들 (여러 옵션 시도)
alternative_xpaths = [
    "//div[@data-cy='job-card']/a",  # 메인 선택자
    "//a[contains(@href, '/wd/')]",  # href에 /wd/가 포함된 링크
    "//div[contains(@class, 'JobCard_JobCard')]/a",  # 클래스명 사용
]

wait = WebDriverWait(driver, 20)  # 대기 시간 증가

# 여러 선택자를 시도하며 요소 찾기
element_found = False
for xpath in alternative_xpaths:
    try:
        print(f"요소 찾기 시도 중: {xpath}")
        wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
        element_xpath = xpath
        element_found = True
        print(f"✓ 요소를 찾았습니다: {xpath}")
        break
    except Exception as e:
        print(f"✗ 타임아웃 또는 오류: {xpath} - {type(e).__name__}")
        continue

if not element_found:
    print("경고: 모든 선택자에서 요소를 찾지 못했습니다.")
    print("기본 XPath로 계속 진행합니다...")
    element_xpath = alternative_xpaths[0]

SCROLL_PAUSE_TIME = 1.5

try:
    last_height = driver.execute_script("return document.body.scrollHeight")
except InvalidSessionIdException:
    print("초기 height를 가져오는 시점에 세션이 끊어졌습니다. (브라우저가 닫힌 상태)")
    driver.quit()
    raise

same_count = 0

while True:
     try:
         # 1) 맨 아래까지 스크롤
         driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
         time.sleep(SCROLL_PAUSE_TIME)
 
         # 2) 새 높이 측정
         new_height = driver.execute_script("return document.body.scrollHeight")
     except (InvalidSessionIdException, WebDriverException) as e:
         print("브라우저 세션이 중간에 끊겼습니다. 스크롤 루프를 종료합니다.")
         print("에러 메시지:", e)
         break
 
     if new_height == last_height:
         same_count += 1
     else:
         same_count = 0
 
     if same_count >= 2:
         print("더 이상 새로 로드되는 공고가 없습니다. 스크롤 종료.")
         break
 
     last_height = new_height

# 여기까지 왔다면, 살아있는 세션 기준으로 elements 수집
elements = []
try:
    # 먼저 찾은 XPath로 시도
    elements = driver.find_elements(By.XPATH, element_xpath)
    print(f"기본 선택자로 {len(elements)}개 발견")
    
    # 요소가 없으면 대체 선택자들 시도
    if not elements:
        print("기본 선택자로 요소를 찾지 못했습니다. 대체 선택자 시도...")
        for xpath in alternative_xpaths:
            try:
                found_elements = driver.find_elements(By.XPATH, xpath)
                if found_elements:
                    elements = found_elements
                    print(f"대체 선택자로 {len(elements)}개 발견: {xpath}")
                    break
            except Exception as e:
                print(f"선택자 {xpath}에서 오류: {e}")
                continue
                
except InvalidSessionIdException:
    print("세션이 이미 종료되어 공고 리스트를 가져올 수 없습니다.")
    elements = []
except Exception as e:
    print(f"요소 수집 중 오류 발생: {e}")
    elements = []

print(f"총 수집된 공고 개수: {len(elements)}")

# 1단계: 리스트 페이지에서 모든 공고의 기본 정보 수집
# 테스트를 위해 3개만 처리
list_data = []
#for idx, e in enumerate(elements[:20]):
for idx, e in enumerate(elements):
    try:
        # Stale Element Reference 방지를 위해 요소를 찾은 직후 모든 속성 추출
        # 재시도 로직 추가
        max_retries = 3
        retry_count = 0
        href = None
        job_category_id = ''
        job_category = ''
        company_id = ''
        company_name = ''
        position_name = ''
        position_id = ''
        
        while retry_count < max_retries:
            try:
                # a 태그의 href 가져오기
                href = e.get_attribute('href')
                print(f"href: {href}")
                # 상대 경로인 경우 전체 URL로 변환
                if href and href.startswith('/'):
                    href = f"https://www.wanted.co.kr{href}"

                
                # data 속성들은 부모 div나 내부 button에 있으므로 부모 요소에서 가져오기
                # 방법 1: 부모 div에서 가져오기
                parent_div = e.find_element(By.XPATH, "./..")  # 부모 div
                
                # 방법 2: 내부 button에서 가져오기 (더 정확)
                try:
                    button = parent_div.find_element(By.XPATH, ".//button[@data-attribute-id='position__bookmark__click']")
                    job_category_id = button.get_attribute('data-job-category-id') or ''
                    job_category = button.get_attribute('data-job-category') or ''
                    company_id = button.get_attribute('data-company-id') or ''
                    company_name = button.get_attribute('data-company-name') or ''
                    position_name = button.get_attribute('data-position-name') or ''
                    position_id = button.get_attribute('data-position-id') or ''
                except:
                    # button을 찾지 못한 경우 부모 div에서 시도
                    job_category_id = parent_div.get_attribute('data-job-category-id') or ''
                    job_category = parent_div.get_attribute('data-job-category') or ''
                    company_id = parent_div.get_attribute('data-company-id') or ''
                    company_name = parent_div.get_attribute('data-company-name') or ''
                    position_name = parent_div.get_attribute('data-position-name') or ''
                    position_id = parent_div.get_attribute('data-position-id') or ''
                
                # 성공적으로 데이터를 가져왔으면 루프 종료
                break
                
            except StaleElementReferenceException:
                retry_count += 1
                if retry_count < max_retries:
                    # 요소를 다시 찾기
                    print(f"Stale element 발생, 재시도 {retry_count}/{max_retries}...")
                    elements = driver.find_elements(By.XPATH, element_xpath)
                    if idx < len(elements):
                        e = elements[idx]
                    else:
                        print(f"인덱스 {idx}가 범위를 벗어났습니다. 스킵합니다.")
                        break
                    time.sleep(0.5)
                else:
                    print(f"최대 재시도 횟수 초과. 이 요소를 스킵합니다.")
                    raise
        
        # 데이터 추출 실패 시 스킵
        if href is None and not job_category_id:
            print(f"요소 {idx+1}에서 데이터를 추출하지 못했습니다. 스킵합니다.")
            continue
        
        # 리스트 페이지 정보 저장 (상세 페이지 정보는 나중에 추가)
        list_data.append({
            'job_category_id': job_category_id,
            'job_category':    job_category,
            'company_id':      company_id,
            'company_name':    company_name,
            'position_name':   position_name,
            'position_id':     position_id,
            'link':            href or '',
        })
        print(f"[{idx+1}/{len(elements)}] 리스트 정보 수집 완료: {company_name} - {position_name}")
    
    except Exception as ex:
        print(f"개별 공고 에러 (인덱스 {idx+1}), 스킵: {ex}")
        continue

# 1단계 완료: 리스트 정보를 먼저 엑셀로 저장
print(f"\n1단계 완료: 리스트 정보 엑셀 저장 중...")
df_list = pd.DataFrame(list_data)
now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
list_save_path = f"C://Users//MULTICAMPUS//Desktop//curosr-playground//wanted//wanted_list_{now_str}.xlsx"
df_list.to_excel(list_save_path, index=False, engine='openpyxl')
print(f"리스트 정보 엑셀 저장 완료: {list_save_path}")

# 2단계: 엑셀을 읽어서 상세 정보 수집
print(f"\n2단계: 엑셀에서 link 정보를 읽어 상세 페이지 정보 수집 시작...")
df_detail = pd.read_excel(list_save_path, engine='openpyxl')

# 상세 정보를 저장할 리스트
detail_info_list = []

for idx, row in df_detail.iterrows():
    try:
        href = row['link']
        
        # href(상세페이지 url)가 없는 경우를 고려해 예외 처리
        if pd.isna(href) or not href:
            # href가 없으면 상세페이지 내용은 전부 빈값/기본값으로 채움
            print(f"[{idx+1}/{len(df_detail)}] 링크가 없어 상세 정보를 수집할 수 없습니다.")
            detail_info_list.append({
                'position': '',
                'content1': '',
                'content2': '',
                'content3': '-',
                'content4': '-',
                'period': '-',
                'skill': ''
            })
            continue
        else:
            # 상세 페이지로 이동하여 정보 추출
            try:
                company_name = row.get('company_name', '')
                position_name = row.get('position_name', '')
                print(f"[{idx+1}/{len(df_detail)}] 상세 페이지 이동 중: {company_name} - {position_name}")
                driver.get(href)
                time.sleep(4)  # 로딩 대기

                # "상세 정보 더 보기" 버튼 클릭 (전체 정보를 보기 위해)
                try:
                    # 여러 방법으로 버튼 찾기 시도
                    more_info_button = None
                    button_selectors = [
                        "//button[@class='wds-j7905l']//span[contains(text(), '상세 정보 더 보기')]/..",  # 클래스명 사용
                        "//span[contains(text(), '상세 정보 더 보기')]/parent::button",  # span에서 부모 button
                        "//button[contains(., '상세 정보 더 보기')]",  # 버튼 내부 텍스트 포함
                        "//button[@aria-labelledby and @type='button']//span[text()='상세 정보 더 보기']/..",  # aria-labelledby 속성 사용
                    ]
                    
                    button_clicked = False
                    for selector in button_selectors:
                        try:
                            more_info_button = driver.find_element(By.XPATH, selector)
                            if more_info_button and more_info_button.is_displayed():
                                # 버튼이 보이는지 확인하고 여러 방법으로 클릭 시도
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", more_info_button)
                                time.sleep(0.5)
                                
                                # 클릭 방법 1: JavaScript 클릭 (가장 안정적)
                                try:
                                    driver.execute_script("arguments[0].click();", more_info_button)
                                    print(f"  ✓ '상세 정보 더 보기' 버튼 클릭 완료 (JavaScript)")
                                    button_clicked = True
                                    time.sleep(1.5)  # 버튼 클릭 후 콘텐츠 로딩 대기
                                    break
                                except Exception as js_error:
                                    print(f"  JavaScript 클릭 실패: {js_error}")
                                
                                # 클릭 방법 2: 일반 click()
                                try:
                                    more_info_button.click()
                                    print(f"  ✓ '상세 정보 더 보기' 버튼 클릭 완료 (일반 클릭)")
                                    button_clicked = True
                                    time.sleep(1.5)
                                    break
                                except ElementClickInterceptedException:
                                    print(f"  일반 클릭 실패: 요소가 가려짐")
                                except Exception as click_error:
                                    print(f"  일반 클릭 실패: {click_error}")
                                
                                # 클릭 방법 3: ActionChains 사용
                                try:
                                    actions = ActionChains(driver)
                                    actions.move_to_element(more_info_button).click().perform()
                                    print(f"  ✓ '상세 정보 더 보기' 버튼 클릭 완료 (ActionChains)")
                                    button_clicked = True
                                    time.sleep(1.5)
                                    break
                                except Exception as action_error:
                                    print(f"  ActionChains 클릭 실패: {action_error}")
                                    
                        except Exception as find_error:
                            continue
                    
                    if not button_clicked:
                        print(f"  ⚠ 모든 클릭 방법 실패 - 버튼 없이 진행합니다")
                        
                except Exception as button_error:
                    print(f"  '상세 정보 더 보기' 버튼 처리 중 오류: {button_error}. 계속 진행합니다...")

                src = driver.page_source
                soup = BeautifulSoup(src, 'lxml')
            except Exception as page_error:
                print(f"[{idx+1}/{len(df_detail)}] 상세 페이지 로딩 실패 ({href}): {page_error}")
                # 기본값으로 채우기
                detail_info_list.append({
                    'position': '',
                    'content1': '',
                    'content2': '',
                    'content3': '-',
                    'content4': '-',
                    'period': '-',
                    'skill': ''
                })
                continue

            try:
                # 포지션 상세 (HTML에서 직접 추출)
                position = ''
                try:
                    # 포지션 상세 섹션의 첫 번째 span에서 내용 추출
                    element_xpath_position = "//h2[contains(text(),'포지션 상세')]/following-sibling::div//span[contains(@class, 'wds-h4ga6o')]"
                    position_elem = driver.find_element(By.XPATH, element_xpath_position)
                    position = position_elem.text.replace('\n', ' ').strip()
                except:
                    try:
                        # 대체 방법: article의 첫 번째 span에서 추출
                        element_xpath_position = "//article[contains(@class, 'JobDescription_JobDescription')]//span[contains(@class, 'wds-h4ga6o')][1]"
                        position_elem = driver.find_element(By.XPATH, element_xpath_position)
                        position = position_elem.text.replace('\n', ' ').strip()
                    except:
                        try:
                            # 대체 방법: meta description에서 추출 (기존 방식)
                            desc_tag = soup.find("meta", {"name": "description"})
                            if desc_tag and desc_tag.get("content"):
                                description_meta = desc_tag.get("content")
                                if "포지션: " in description_meta:
                                    position = description_meta.split("포지션: ")[1].split("\n")[0].strip()
                        except:
                            position = ''

                # 주요업무 (HTML에서 직접 추출)
                content1 = ''
                try:
                    element_xpath_content1 = "//h3[contains(text(),'주요업무')]/parent::div"
                    content1_elem = driver.find_element(By.XPATH, element_xpath_content1)
                    content1 = content1_elem.text.replace('주요업무\n', '').replace('• ', '').replace('\n', ' ').strip()
                except:
                    try:
                        # 대체 방법: span에서 직접 추출
                        element_xpath_content1 = "//h3[contains(text(),'주요업무')]/following-sibling::span[contains(@class, 'wds-h4ga6o')]"
                        content1_elem = driver.find_element(By.XPATH, element_xpath_content1)
                        content1 = content1_elem.text.replace('• ', '').replace('\n', ' ').strip()
                    except:
                        content1 = ''

                # 자격요건
                content2 = ''
                try:
                    element_xpath_content2 = "//h3[contains(text(),'자격요건')]/parent::div"
                    content2_elem = driver.find_element(By.XPATH, element_xpath_content2)
                    content2 = content2_elem.text.replace('자격요건\n', '').replace('• ', '').replace('\n', ' ').strip()
                except:
                    try:
                        # 대체 방법: span에서 직접 추출
                        element_xpath_content2 = "//h3[contains(text(),'자격요건')]/following-sibling::span[contains(@class, 'wds-h4ga6o')]"
                        content2_elem = driver.find_element(By.XPATH, element_xpath_content2)
                        content2 = content2_elem.text.replace('• ', '').replace('\n', ' ').strip()
                    except:
                        content2 = ''

                # 우대사항
                content3 = '-'
                try:
                    element_xpath_content3 = "//h3[contains(text(),'우대사항')]/parent::div"
                    content3_elem = driver.find_element(By.XPATH, element_xpath_content3)
                    content3 = content3_elem.text.replace('우대사항\n', '').replace('• ', '').replace('\n', ' ').strip()
                except:
                    try:
                        # 대체 방법: span에서 직접 추출
                        element_xpath_content3 = "//h3[contains(text(),'우대사항')]/following-sibling::span[contains(@class, 'wds-h4ga6o')]"
                        content3_elem = driver.find_element(By.XPATH, element_xpath_content3)
                        content3 = content3_elem.text.replace('• ', '').replace('\n', ' ').strip()
                    except:
                        content3 = '-'

                # 혜택 및 복지
                content4 = '-'
                try:
                    element_xpath_content4 = "//h3[contains(text(),'혜택 및 복지')]/parent::div"
                    content4_elem = driver.find_element(By.XPATH, element_xpath_content4)
                    content4 = content4_elem.text.replace('혜택 및 복지\n', '').replace('• ', '').replace('\n', ' ').strip()
                except:
                    try:
                        # 대체 방법: span에서 직접 추출
                        element_xpath_content4 = "//h3[contains(text(),'혜택 및 복지')]/following-sibling::span[contains(@class, 'wds-h4ga6o')]"
                        content4_elem = driver.find_element(By.XPATH, element_xpath_content4)
                        content4 = content4_elem.text.replace('• ', '').replace('\n', ' ').strip()
                    except:
                        content4 = '-'
                # 마감일
                period = '-'
                try:
                    element_xpath2 = "//h2[contains(text(),'마감일')]/parent::article"
                    period = driver.find_element(By.XPATH, element_xpath2).text.replace('마감일\n','')
                except:
                    period = '-'
                # 기술스택
                skill = ''
                try:
                    element_xpath = "//h2[contains(text(),'기술 스택 • 툴')]/parent::article"
                    skill_list = driver.find_element(By.XPATH, element_xpath).text.replace('기술 스택 • 툴\n','').split('\n')
                    skill = "::".join(skill_list)
                except:
                    skill = ''

                # detail_info_list에 상세 정보 추가
                detail_info_list.append({
                    'position': position,
                    'content1': content1,
                    'content2': content2,
                    'content3': content3,
                    'content4': content4,
                    'period': period,
                    'skill': skill
                })
                
                print(f"[{idx+1}/{len(df_detail)}] 상세 정보 수집 완료")
                
            except Exception as detail_error:
                print(f"[{idx+1}/{len(df_detail)}] 상세 페이지 정보 추출 실패 ({href}): {detail_error}")
                # 기본값으로 채우기
                detail_info_list.append({
                    'position': '',
                    'content1': '',
                    'content2': '',
                    'content3': '-',
                    'content4': '-',
                    'period': '-',
                    'skill': ''
                })
        
    except Exception as ex:
        print(f"개별 상세 페이지 처리 에러 (인덱스 {idx+1}), 스킵: {ex}")
        # 기본값으로 채우기
        detail_info_list.append({
            'position': '',
            'content1': '',
            'content2': '',
            'content3': '-',
            'content4': '-',
            'period': '-',
            'skill': ''
        })
        continue

# 3단계: 상세 정보를 엑셀에 컬럼 추가하여 저장
print(f"\n2단계 완료: 총 {len(detail_info_list)}개 상세 정보 수집 완료. 엑셀 업데이트 중...")

# 상세 정보를 DataFrame으로 변환
df_detail_info = pd.DataFrame(detail_info_list)

# 기존 엑셀 데이터와 상세 정보를 합치기
df_final = pd.concat([df_detail, df_detail_info], axis=1)

# 최종 엑셀 저장 (리스트 정보 + 상세 정보)
final_save_path = f"C://Users//MULTICAMPUS//Desktop//curosr-playground//wanted//wanted_final_{now_str}.xlsx"

# to_excel()은 encoding 파라미터를 지원하지 않습니다 (엑셀은 기본적으로 UTF-8 지원)
# 한글 깨짐 방지를 위해 engine을 명시적으로 지정
df_final.to_excel(final_save_path, index=False, engine='openpyxl')
print(f"최종 엑셀 저장 완료: {final_save_path}")
print(f"  - 리스트 정보 파일: {list_save_path}")
print(f"  - 최종 통합 파일: {final_save_path}")




# 원하면 자동 종료
# driver.quit()
