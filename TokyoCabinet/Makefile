CXX=g++
CXX_LIBS=-ltokyocabinet

tokyo_cabinet_set: tokyo_cabinet_set.cpp
	$(CXX) -std=c++11 -ggdb3 $< -o $@ $(CXX_LIBS)

clean:
	rm -rf tokyo_cabinet_set

.PHONY: clean
