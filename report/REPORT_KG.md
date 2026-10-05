# Báo cáo Day 19 — Flat RAG vs GraphRAG

**Họ tên:** Chu Văn Nhân  **MSSV:** 2A202602668  **Ngày:** 05-10-2026

Nguồn số liệu: [benchmark sinh bằng `bench_kg.py --judge`](../ket_qua_benchmark_kg.txt). Thiết kế: [ONTOLOGY.md](ONTOLOGY.md). Dùng ontology gợi ý, không đăng ký bonus.

Chat và judge: Ollama Cloud `gpt-oss:120b`; embedding: Ollama local `bge-m3`. Corpus: 18 điều luật + 20 bài báo; 176 chunk, `chunk_size=800`, `top_k=3`. Graph cuối: **209 node / 387 cạnh**. Đây là một lần chạy, không phải trung bình nhiều lần.

## 1. Chi phí

Hai bảng nguyên văn từ benchmark:

```text
== Indexing (one-off)
pipeline  calls    in_tok  out_tok       USD  seconds
flat        176     31455        0   0.00000    119.3
graph       196     68541    15060   0.00000    176.4

== Querying (mean per question)
pipeline  recall  judge   in_tok  out_tok       USD  seconds
flat        0.38   1.17      792      450   0.00000     3.38
graph       0.38   1.67     6522      635   0.00000     3.82
```

| Chỉ số | Flat | Graph | Graph / Flat |
| --- | --- | --- | --- |
| Indexing USD theo bộ đếm | 0.00000 | 0.00000 | Không xác định (0/0) |
| Indexing giây | 119.3 | 176.4 | 1.48× |
| Mỗi câu: USD theo bộ đếm | 0.00000 | 0.00000 | Không xác định (0/0) |
| Mỗi câu: giây | 3.38 | 3.82 | 1.13× |
| Mỗi câu: in_tok | 792 | 6522 | 8.23× |
| Mỗi câu: out_tok | 450 | 635 | 1.41× |

Graph dùng lại vector index của Flat và thêm 20 lần trích xuất tin: 37,086 input token, 15,060 output token và khoảng 57.1 giây. Luật được trích bằng regex, không gọi LLM. Khi truy vấn, toàn văn khoản luật và dữ kiện graph làm input tăng khoảng 5,730 token/câu.

USD = 0 là cách bộ đếm biểu diễn provider hiện tại: embedding local không có phí API nhưng vẫn dùng điện/phần cứng; phí gói/quota Ollama Cloud chưa được quy đổi sang token. Không kết luận dịch vụ miễn phí, không tính tỷ lệ chi phí tiền từ 0/0. Với độ trễ đo được, Graph vừa có indexing cao hơn vừa có truy vấn trung bình chậm hơn nên không có điểm hòa vốn về thời gian; lợi ích là chất lượng Q3/Q5.

## 2. Từng câu hỏi

| Câu | Loại | Flat recall / judge | Graph recall / judge | Thắng | Vì sao |
| --- | --- | --- | --- | --- | --- |
| Q1 | single-hop-law | 1.00 / 2 | 1.00 / 2 | Hòa | Cả hai lấy đúng định nghĩa tiền chất; Graph bổ sung Điều 2 khoản 4. |
| Q2 | single-hop-news | 0.00 / 2 | 0.00 / 2 | Hòa | Cả hai nêu đúng Trần Thanh Tuấn và Trần Minh Tâm; recall bị khoảng trắng Unicode làm sai. |
| Q3 | cross-kb | 0.00 / 1 | 0.00 / 2 | Graph | Flat thiếu cơ sở luật; Graph nêu Điều 251, khoản 1, 02–07 năm và án 36 tháng. |
| Q4 | cross-kb | 0.33 / 1 | 0.33 / 1 | Không bên nào đúng đủ | Flat bịa khung 5–20 năm; Graph nhầm mức tối đa khoản 1 là tối đa toàn điều. |
| Q5 | cross-kb-multi-hop | 0.60 / 0 | 0.60 / 2 | Graph | Flat nhầm Điều 255; Graph nối đúng Điều 250 khoản 4 và khung 20 năm, chung thân hoặc tử hình. |
| Q6 | aggregation | 0.33 / 1 | 0.33 / 1 | Không bên nào đủ | Flat chỉ liệt kê ba vụ; Graph có hai tên vụ của Cái Quang Huy và không gộp rõ ràng. |

Trên Q3–Q5, recall trung bình cùng khoảng 0.31, nhưng judge Flat = 0.67 và Graph = 1.67. Graph cải thiện cơ sở pháp lý ở Q3/Q5; không được tuyên bố recall cao hơn vì kết quả thực tế không cho thấy điều đó. Judge dùng cùng model với model trả lời, không phải thẩm định pháp lý độc lập.

## 3. Phân tích lỗi

### E2 — Lọc khoản làm thiếu mức phạt tối đa

- **Hiện tượng:** Q4 Graph trả mức tối đa 7 năm, trong khi khoản 4 Điều 255 có tù chung thân.
- **Bằng chứng:** Q4 Graph trong benchmark viết: “mức **phạt tù tối đa** cho hành vi ‘tổ chức sử dụng trái phép chất ma túy’ là **7 năm** tù.” Khoảng trắng trong trích dẫn được hiển thị lại bằng khoảng trắng thường; nội dung không đổi. Truy vấn trên graph sau benchmark:

```cypher
MATCH (:Article {id:'Điều 255 BLHS'})-[:HAS_CLAUSE]->(cl:Clause)
RETURN cl.number AS clause, cl.penalty AS penalty ORDER BY clause;
```

```text
1 | phạt tù từ 02 năm đến 07 năm
2 | phạt tù từ 07 năm đến 15 năm
3 | phạt tù từ 15 năm đến 20 năm
4 | phạt tù 20 năm hoặc tù chung thân
5 | phạt tiền từ 50.000.000 đồng đến 500.000.000 đồng, phạt quản chế, cấm cư trú từ 01 năm đến 05 năm hoặc tịch thu một phần hoặc toàn bộ tài sản
```

- **Nguyên nhân:** `Neo4jGraph.context` mở rộng vụ sang luật nhưng ưu tiên khoản 1 hoặc khoản nhắc chất của vụ. Các tình tiết tăng nặng không cần nhắc tên chất bị bỏ sót; model đồng nhất mức tối đa khoản cơ bản với toàn điều.
- **Đề xuất sửa:** Với câu hỏi mức tối đa, lấy mọi khoản của điều được nối trước khi giới hạn dữ kiện, rồi yêu cầu phân biệt tối đa toàn điều và khung áp dụng cho vụ. Đánh đổi: prompt dài hơn, tăng token; cần test Q4 riêng. Giữ nguyên baseline trong lần báo cáo này, không sửa benchmark để nâng điểm.

### E3 — Một chất và một vụ thành nhiều node

- **Hiện tượng:** Graph có cả `Ketamine` / `ketamine` và `Methamphetamine` / `methamphetamine`. Q6 Graph liệt kê hai vụ Cái Quang Huy dưới hai tên, gây đếm trùng.
- **Bằng chứng:**

```cypher
MATCH (s:Substance) RETURN s.name AS name ORDER BY toLower(s.name);
```

```text
Amphetamine, Cocaine, côca, cần sa, Heroine, Ketamine, ketamine,
MDMA, Methamphetamine, methamphetamine, thuốc phiện, XLR-11
```

Q6 Graph liệt kê cả “Vụ vận chuyển ma túy của Cái Quang Huy” và “Vụ vận chuyển ma túy của Cái Quang Huy và Nguyễn Tiến Đạt”.

- **Nguyên nhân:** Khóa `MERGE` là tên nguyên văn; prompt đề nghị tên chất chuẩn nhưng chưa cưỡng chế chuẩn hóa sau extraction. Tên vụ do LLM đặt khác nhau giữa bài báo; uniqueness theo tên không nhận ra cùng sự kiện.
- **Đề xuất sửa:** Chuẩn hóa chất bằng bảng tên chuẩn không phân biệt hoa/thường trước `MERGE`; với vụ, tách bài báo khỏi sự kiện và dùng ID sự kiện có kiểm chứng. Đánh đổi: gộp sai có thể trộn hai vụ khác nhau; không nên chỉ gộp theo tên người.

### E4 — Recall thấp dù câu trả lời đúng

- **Hiện tượng:** Q2 cả hai pipeline có recall 0.00 nhưng judge 2; Q3 Graph có recall 0.00 nhưng judge 2.
- **Bằng chứng:** Q2 Flat nêu đúng hai người: `Trần Thanh\u202fTuấn`, `Trần\u202fMinh\u202fTâm`; Q3 Graph có `36\u202ftháng` và `Điều\u202f251`. Đây là cách biểu diễn mã Unicode của các chuỗi thật trong benchmark; `\u202f` là narrow no-break space, không phải khoảng trắng ASCII.
- **Nguyên nhân:** `keyword_recall` chỉ gọi `.lower()` rồi kiểm tra substring; từ khóa dùng khoảng trắng ASCII không khớp U+202F. Phép đo còn phụ thuộc cách diễn đạt “02–07 năm” so với từ khóa.
- **Đề xuất sửa:** Chuẩn hóa Unicode và khoảng trắng trong cả answer và keyword, đồng thời giữ judge và đọc câu trả lời. Cần thêm test cho U+202F; không sửa phép đo gốc của lab để tạo điểm tốt hơn.

## 4. Kết luận

KG phù hợp khi cần nối vụ trong tin với quy phạm luật: judge Q3 tăng 1→2, Q5 tăng 0→2. Flat đủ cho định nghĩa và thông tin trong một bài (Q1/Q2 đều judge 2), chi phí dựng và input token thấp hơn.

Đổi lại, Graph cần 176.4 giây dựng thay vì 119.3 giây, input trung bình 6,522 thay vì 792 token, và vẫn sai Q4 do chọn thiếu khoản. Aggregation Q6 còn cần chuẩn hóa sự kiện và nguồn; graph không tự bảo đảm tính đúng pháp lý. Kết quả chỉ phản ánh corpus lưu trong repo, không xác nhận luật hiện hành hoặc kết quả xử lý vụ án ngoài corpus.

## 5. Tự kiểm

Thực hiện trước benchmark; không chạy lại `--check` sau benchmark vì lệnh này thay graph đầy đủ bằng luật + một bài.

```text
$ python -m pytest tests -q
...................................................                      [100%]
51 passed in 1.93s

$ python bench_kg.py --check
[OK] Dữ liệu: 18 điều luật, 20 bài báo
[OK] KG-1 link_entity
[OK] Neo4j kết nối được
[provider] chat = ollama:gpt-oss:120b | embedding = ollama_local:bge-m3
[OK] KG-2 build_graph: 148 node / 294 cạnh, đường xuyên 2 KB dài 1 cạnh
[OK] KG-3 context: 23 dữ kiện, có Điều 251
[OK] KG-4 GraphRAGAgent.answer
[OK] Chi phí check: 1 lần gọi LLM, $0.00000. Graph nhỏ (luật + 1 bài) vẫn còn trong Neo4j để bạn xem; chạy --judge để dựng graph đầy đủ.
```

Graph sau `--judge`: Article 18, Clause 99, Crime 13, Substance 12, Person 45, Case 15, Location 7; tổng 209 node. Quan hệ: MENTIONS 169, HAS_CLAUSE 99, INVOLVED_IN 54, CHARGED_WITH 20, INVOLVES 17, LOCATED_IN 15, DEFINES 13; tổng 387 cạnh. Có 20 bài đầu vào nhưng không tương đương 20 vụ: extraction có thể không có vụ hoặc nhiều bài gộp cùng tên vụ.

Ảnh chụp trực tiếp Neo4j Browser từ graph cuối, không dùng ảnh mẫu:
- [Đếm node](img/kg_count.png)
- [Cầu nối hai KB](img/kg_cross_kb.png)
- [Vụ Cái Quang Huy](img/kg_my_case.png)

Người chọn cho Q-D: **Cái Quang Huy**, không phải Lê Minh Thành.

## Vấn đề gặp phải

Neo4j ban đầu chưa chạy: `SETUP-2` tại `bolt://localhost:7687`; Docker Desktop chưa bật. Đã mở Docker Desktop, khởi động container `neo4j-drug-kg`, kiểm tra HTTP 200 tại cổng 7474 và chạy lại `--check` thành công. Model local `bge-m3:latest` có sẵn; benchmark xác nhận embedding dùng `ollama_local:bge-m3`.

Các giới hạn E2/E3/E4 vẫn được ghi nhận, không che giấu hoặc chỉnh tay file benchmark. Chưa thực hiện bonus ontology, commit/push hay nộp vlearn.
